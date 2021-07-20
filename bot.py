#!/usr/bin/python3
import logging
import os
import re
from os import environ, SEEK_END
from typing import TextIO

import telegram
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, JobQueue
from mcrcon import MCRcon, MCRconException

load_dotenv()
TELEGRAM_BOT_BASE_URL = environ.get('TELEGRAM_BOT_BASE_URL', None)
LOG_FILE_PATH = environ["LOG_FILE_PATH"]
BOT_TOKEN = environ["BOT_TOKEN"]
CHAT = int(environ["CHAT_ID"])
RCON_PASSWORD = environ.get("RCON_PASSWORD", "")
rcon = MCRcon("127.0.0.1", RCON_PASSWORD)

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.WARN
)

logger = logging.getLogger(__name__)


# Define a few command handlers. These usually take the two arguments update and
# context. Error handlers also receive the raised TelegramError object in error.
def start(update: Update, _context: CallbackContext) -> None:
    """Send a message when the command /start is issued."""
    update.message.reply_text('Hi!')


def help_command(update: Update, _context: CallbackContext) -> None:
    """Send a message when the command /help is issued."""
    update.message.reply_text('我现在主要是在 Telegram 和 Minecraft 之间转发。')

def list_players(update: Update, context: CallbackContext):
    context.bot.send_message(CHAT, rcon.command('list'))

def set_time(update: Update, context: CallbackContext):
    error_reply = '请带上时间设置参数，比如 `0`, `noon`, `day`, `night`, `midnight`\n' \
                  '[详细请看这里](https://minecraft-zh.gamepedia.com/昼夜更替)。'

    def when_error():
        update.message.reply_text(error_reply, parse_mode=telegram.ParseMode.MARKDOWN_V2)

    if len(context.args) != 1:
        when_error()
        return
    arg: str = context.args[0].strip().lower()
    if arg not in ('noon', 'day', 'night', 'midnight'):
        try:
            int(arg)
        except ValueError:
            when_error()
            return
    rcon.command("time set {}".format(arg))


def forward_to_minecraft(update: Update, _context: CallbackContext) -> None:
    """Echo the user message."""
    message = update.message
    if not message:
        return
    sender = message.from_user
    if not sender:
        return
    name = sender.first_name
    if sender.last_name:
        name += ' ' + sender.last_name

    rcon.command("say [Telegram][{}] {}".format(name, message.text))


def log_filter(log: str) -> bool:
    pass_list = [
        'has made the advancement',
        '[Async Chat Thread',
    ]
    for s in pass_list:
        if log.find(s) != -1:
            return True
    if log.find("] [Server thread/INFO]") == -1:
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
        '[Telegram]',
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


def log_sender(bot: telegram.Bot, log_file: TextIO):
    # get new logs.
    logs = log_file.readlines()
    text = ""
    for log in filter(log_filter, logs):
        text += log_mapper(log)
    length = len(text)
    if length < 3 or length > 1024:
        log_file.seek(0, SEEK_END)
        return
    bot.send_message(CHAT, text, disable_web_page_preview=True, disable_notification=True)


LOG_FILE_KEY = 'LOG_FILE'
LOG_FILE_INO_KEY = 'LOG_FILE_INO'


def log_watch(context: CallbackContext):
    log_stat = os.stat(LOG_FILE_PATH)
    if context.bot_data.get(LOG_FILE_INO_KEY, None) != log_stat.st_ino \
            or LOG_FILE_KEY not in context.bot_data \
            or context.bot_data[LOG_FILE_KEY].closed:
        log_file = open(LOG_FILE_PATH)
        context.bot_data[LOG_FILE_KEY] = log_file
        context.bot_data[LOG_FILE_INO_KEY] = log_stat.st_ino
        log_file.seek(0, SEEK_END)
        return
    log_file: TextIO = context.bot_data[LOG_FILE_KEY]
    log_sender(context.bot, log_file)


def spawn_log_watch(job_queue: JobQueue):
    job_queue.run_repeating(log_watch, interval=1, first=0, name='log_watch')


def daemon(context: CallbackContext):
    if not context.job_queue.get_jobs_by_name('log_watch'):
        context.bot.send_message(CHAT, '我炸了！等20秒')
        context.job_queue.run_once(lambda ctx: spawn_log_watch(ctx.job_queue), when=20)
    try:
        rcon.connect()
    except (MCRconException, ConnectionError) as e:
        context.bot.send_message(CHAT, f'我炸了！等20秒 (`{e}`)', telegram.ParseMode.MARKDOWN_V2)

def edit_group_name(context: CallbackContext):
    online = rcon.command('list')
    if not online:
        return
    matched = re.search(r'\d+', online)
    if not matched:
        return
    online_counter = matched.group(0)
    if online_counter == '0':
        context.bot.set_chat_title(CHAT, f'炸魚禁止 (没人玩)', timeout=200)
    else:
        context.bot.set_chat_title(CHAT, f'炸魚禁止 ({online_counter}人游戏中)', timeout=200)

def main():
    rcon.connect()
    """Start the bot."""
    updater = Updater(BOT_TOKEN, base_url=TELEGRAM_BOT_BASE_URL)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(CommandHandler("list", list_players))
    dispatcher.add_handler(CommandHandler("time", set_time))

    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, forward_to_minecraft))
    dispatcher.job_queue.run_repeating(edit_group_name, interval=10, first=0)
    dispatcher.job_queue.run_repeating(daemon, interval=60*3, first=0)
    spawn_log_watch(dispatcher.job_queue)

    updater.start_polling()

    updater.idle()
    rcon.disconnect()


if __name__ == '__main__':
    main()
