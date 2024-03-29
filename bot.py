#!/usr/bin/env python
from io import SEEK_END
import os
import re
import logging
import random
from asyncio import sleep
from typing import TextIO

from dotenv import load_dotenv
from aiomcrcon import Client as RconClient
from telegram import ForceReply, Update, Bot, error
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, JobQueue, filters

load_dotenv()

TELEGRAM_BOT_BASE_URL = os.environ.get('TELEGRAM_BOT_BASE_URL', None)
LOG_FILE_PATH = os.environ["LOG_FILE_PATH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT = int(os.environ["CHAT_ID"])
TITLE = os.environ.get('CHAT_TITLE', '')
RCON_PASSWORD = os.environ.get("RCON_PASSWORD", "")

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.WARN
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

async def command(cmd: str):
    rcon = RconClient("127.0.0.1", 25575, RCON_PASSWORD)
    await rcon.connect()
    resp, _ = await rcon.send_cmd(cmd)
    await rcon.close()
    return resp

# Define a few command handlers. These usually take the two arguments update and
# context.
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    await update.message.reply_html(
        rf"Hi {user.mention_html()}!",
        reply_markup=ForceReply(selective=True),
    )


sad_kaomoji = [
    '(。_。)',
    '(。﹏。)',
    '(；▽；)',
    '(´•̥ ̯ •̥`)',
];

async def show_error_title(bot: Bot, sleep_sec=4):
    await bot.set_chat_title(CHAT, f'{TITLE} (???)')
    await sleep(sleep_sec)


async def edit_group_name(context: ContextTypes.DEFAULT_TYPE):
    prev_online_count = -1
    while True:
        await sleep(1)
        try: 
            online = await command('list')
        except:
            await show_error_title(context.bot)
            prev_online_count = -1
            continue
        if not online:
            continue
        matched = re.search(r'\d+', online)
        if not matched:
            await sleep(4)
            continue
        online_count = matched.group(0)
        if online_count == prev_online_count:
            await sleep(2)
            continue
        prev_online_count = online_count
        try:
            if online_count == '0':
                sad = '(没人玩)'
                if random.random() < 0.4:
                    random.shuffle(sad_kaomoji)
                    sad = sad_kaomoji[0]
                await context.bot.set_chat_title(CHAT, f'{TITLE} {sad}'.strip())
            else:
                await context.bot.set_chat_title(CHAT, f'{TITLE} ({online_count}人游戏中)')
        except:
            show_error_title(context.bot)
            prev_online_count = -1
            continue


async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(await command('list'))

async def allow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message.chat_id != CHAT:
        return
    await command('whitelist off')
    await update.message.reply_text('已关闭白名单，1分钟后再次开启')
    await sleep(60)
    await command('whitelist on')

async def forward_to_minecraft(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if not message:
        return
    sender = message.from_user
    if not sender:
        return
    name = sender.first_name
    if sender.last_name:
        name += ' ' + sender.last_name
    await command(f"say [Telegram][{name}] {message.text}")


async def set_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    error_reply = '请带上时间设置参数，比如 `0`, `noon`, `day`, `night`, `midnight`\n' \
                  '[详细请看这里](https://minecraft-zh.gamepedia.com/昼夜更替)。'

    async def when_error():
        await update.message.reply_text(error_reply, parse_mode=ParseMode.MARKDOWN_V2)

    if len(context.args) != 1:
        await when_error()
        return
    arg: str = context.args[0].strip().lower()
    if arg not in ('noon', 'day', 'night', 'midnight'):
        try:
            int(arg)
        except ValueError:
            await when_error()
            return
    await command("time set {}".format(arg))


def log_filter(log: str) -> bool:
    pass_list = [
        'has made the advancement',
        '[Async Chat Thread',
    ]
    found = lambda s: log.find(s) != -1
    for s in pass_list:
        if found(s):
            return True
    if not found("] [Server thread/INFO]"):
        return False
    skip_list = [
        'issued server command: /me',
        'issued server command: /tell',
        'issued server command: /help',
        'issued server command: /w',
        'issued server command: /msg',
        ' left the game',
        ' logged in with entity id',
        'lost connection',
        "Can't keep up! Is the server overloaded?",
        'moved too quickly',
        '[Telegram]',
        '[Hibernate]',
        'Skipping update ',
    ]
    for s in skip_list:
        if log.find(s) != -1:
            return False
    return True

IP_MATCH = re.compile(r"\[/\d+\.\d+\.\d+\.\d+:\d+]")
HEAD_MATCH = re.compile(r"^\[\d+:\d+:\d+] \[[^]]+]:\s+")


def log_mapper(log: str) -> str:
    log = HEAD_MATCH.sub("", log)
    log = IP_MATCH.sub("", log)
    log = log.replace("[m", "")
    return log


async def log_sender(bot: Bot, log_file: TextIO):
    # get new logs.
    logs = log_file.readlines()
    text = ""
    for log in filter(log_filter, logs):
        text += log_mapper(log)
    length = len(text)
    if length < 3 or length > 1024:
        log_file.seek(0, SEEK_END)
        return
    await bot.send_message(CHAT, text, disable_web_page_preview=True, disable_notification=True)


LOG_FILE_KEY = 'LOG_FILE'
LOG_FILE_INO_KEY = 'LOG_FILE_INO'


async def log_watch(context: ContextTypes.DEFAULT_TYPE):
    log_stat = os.stat(LOG_FILE_PATH)
    prev_log_ino = None
    log_file = open(LOG_FILE_PATH)

    while True:
        log_stat = os.stat(LOG_FILE_PATH)
        # when log file rotated or closed
        if prev_log_ino != log_stat.st_ino or log_file.closed:
            log_file = open(LOG_FILE_PATH)
            prev_log_ino = log_stat.st_ino
            log_file.seek(0, SEEK_END)
        try:
            await log_sender(context.bot, log_file)
        except Exception as e:
            show_error_title(context.bot)
            logger.error("Error on sending logs", e)
        await sleep(1)

async def status_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_chat_title = update.message.new_chat_title
    if not new_chat_title:
        return
    key = 'chat_title_status_id'
    if key not in context.chat_data:
        context.chat_data[key] = update.message.message_id
        return
    prev_id = context.chat_data[key]
    try:
        await context.bot.delete_message(CHAT, prev_id)
    except error.BadRequest:
        pass
    context.chat_data[key] = update.message.message_id    

def main() -> None:
    """Start the bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(BOT_TOKEN).build()

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("list", list_command))
    application.add_handler(CommandHandler("allow", allow))
    application.add_handler(CommandHandler("time", set_time))

    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_TITLE, status_update))
    # on non command i.e message - echo the message on Telegram
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, forward_to_minecraft))

    application.job_queue.run_once(log_watch, when=4, name='log_watch')

    if TITLE != "":
        application.job_queue.run_once(edit_group_name, when=4)
    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()