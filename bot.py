#!/usr/bin/env python
from io import SEEK_END
import os
import re
import logging
import random
from asyncio import sleep
from datetime import datetime, timezone, timedelta
from typing import TextIO

from dotenv import load_dotenv
from aiomcrcon import Client as RconClient  # type: ignore[import-untyped]
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

SLEEPING = 'zzZ'

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.WARN
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

async def command(cmd: str) -> str:
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
    message = update.message
    if user is None or message is None:
        return
    await message.reply_html(
        rf"Hi {user.mention_html()}!",
        reply_markup=ForceReply(selective=True),
    )

sad_kaomoji = [
    '(。_。)',
    '(。﹏。)',
    '(；▽；)',
    '(´•̥ ̯ •̥`)',
];

async def show_error_title(bot: Bot, sleep_sec: int = 4) -> None:
    await bot.set_chat_title(CHAT, f'{TITLE} (zzZ)')
    await sleep(sleep_sec)


async def edit_group_name(context: ContextTypes.DEFAULT_TYPE) -> None:
    first_time = True
    prev_count: int | str = SLEEPING
    while True:
        await sleep(15)
        count: int | str = SLEEPING
        try:
            online = await command('list')
            if online:
                matched = re.search(r'\d+', online)
                if matched:
                    count = int(matched.group(0))
        except Exception as e:
            pass
        if prev_count == count and not first_time:
            continue
        first_time = False
        prev_count = count
        try:
            if count == SLEEPING:
                logger.info('all sleeping')
                await context.bot.set_chat_title(CHAT, f'{TITLE} (zzZ)')
            elif count == 0:
                sad = '(没人玩)'
                if random.random() < 0.4:
                    random.shuffle(sad_kaomoji)
                    sad = sad_kaomoji[0]
                await context.bot.set_chat_title(CHAT, f'{TITLE} {sad}'.strip())
            else:
                await context.bot.set_chat_title(CHAT, f'{TITLE} ({count})')
        except Exception as e:
            logger.error(e)
            continue


async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        local = await command('list')
    except:
        local = SLEEPING

    message = update.message
    if message is None:
        return
    await message.reply_text(
        f'[{TITLE}]\n\n' + local,
    )

async def allow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if message is None:
        return
    error_reply = '请带上用户名`\n'

    async def when_error() -> None:
        await message.reply_text(error_reply, parse_mode=ParseMode.MARKDOWN_V2)

    if context.args is None or len(context.args) != 1:
        await when_error()
        return
    arg: str = context.args[0].strip()
    try:
        await command("whitelist add {}".format(arg))
    except:
        await message.reply_text('设置白名单失败, 可能服务器休眠中。')

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
    try:
        await command(f"say [Telegram][{name}] {message.text}")
    except:
        return


async def set_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if message is None:
        return
    error_reply = '请带上时间设置参数，比如 `0`, `noon`, `day`, `night`, `midnight`\n' \
                  '[详细请看这里](https://minecraft-zh.gamepedia.com/昼夜更替)。'

    async def when_error() -> None:
        await message.reply_text(error_reply, parse_mode=ParseMode.MARKDOWN_V2)

    if context.args is None or len(context.args) != 1:
        await when_error()
        return
    arg: str = context.args[0].strip().lower()
    if arg not in ('noon', 'day', 'night', 'midnight'):
        try:
            int(arg)
        except ValueError:
            await when_error()
            return
    try:
        await command("time set {}".format(arg))
    except:
        await message.reply_text('设置时间失败, 可能服务器休眠中。')

async def set_weather(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if message is None:
        return
    error_reply = '请带上参数，比如 `clear`、`rain`、`thunder`\n' \

    async def when_error() -> None:
        await message.reply_text(error_reply, parse_mode=ParseMode.MARKDOWN_V2)

    if context.args is None or len(context.args) != 1:
        await when_error()
        return
    arg: str = context.args[0].strip().lower()
    if arg not in ('clear', 'rain', 'thunder'):
        await when_error()
        return
    try:
        await command("weather {}".format(arg))
    except:
        await message.reply_text('设置天气失败, 可能服务器休眠中。')

async def set_whitelist(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if message is None:
        return
    error_reply = '请带上参数，比如 `on`、`off`\n' \

    async def when_error() -> None:
        await message.reply_text(error_reply, parse_mode=ParseMode.MARKDOWN_V2)

    if context.args is None or len(context.args) != 1:
        await when_error()
        return
    arg: str = context.args[0].strip().lower()
    if arg not in ('on', 'off'):
        await when_error()
        return
    try:
        await command("whitelist {}".format(arg))
    except:
        await message.reply_text('设置白名单开关失败, 可能服务器休眠中。')


async def clear_arrow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    try:
        await command("kill @e[type=arrow]")
    except:
        if message is not None:
            await message.reply_text('清除箭矢失败, 可能服务器休眠中。')


def log_filter(log: str) -> bool:
    pass_list = [
        'has made the advancement',
        '[Async Chat Thread',
        'For help, type "help"'
    ]
    found = lambda s: log.find(s) != -1
    for s in pass_list:
        if found(s):
            return True
    if not found("] [Server thread/INFO]"):
        return False
    if 'net.minecraft.server.MinecraftServer' not in log:
        return False
    skip_list = [
        'issued server command: /me',
        'issued server command: /tell',
        'issued server command: /help',
        'issued server command: /w',
        'issued server command: /msg',
        'Preparing spawn area',
        '[TabTPS]',
        '[BlueMap]',
        '[spark]',
        '[MoonriseCommon]',
        '[ChunkTaskScheduler]',
        'Paper:',
        '[SpigotLibraryLoader]',
        'Preparing start',
        'Time elapsed:',
        ' logged in with entity id',
        'lost connection',
        'RCON',
        'permissions.yml',
        "Can't keep up! Is the server overloaded?",
        'moved too quickly',
        '[Telegram]',
        '[防沉迷温馨提示]',
        '[Hibernate]',
        '[ChunkHolderManager]',
        'Skipping update ',
        'Generating keypair',
        'Using epoll channel type',
        'Preparing level "world"',
        'Running delayed init tasks',
        'Starting remote control listener',
        '【YSM】',
        'This server is running Paper version',
    ]
    for s in skip_list:
        if log.find(s) != -1:
            return False
    return True

IP_MATCH = re.compile(r"\[/\d+\.\d+\.\d+\.\d+:\d+]")
HEAD_MATCH = re.compile(r"^\[\d+:\d+:\d+] \[[^]]+]:\s+")


def log_mapper(log: str) -> str:
    if '/]: ' in log:
        log = log.split('/]: ', 1)[1]
    log = log.removeprefix('[Not Secure] ')
    return log

async def process_log_cmd(line: str) -> None:
    if '!' in line:
        line = line.split('!', 1)[1]
    args = line.split()
    cmd = args[0]
    args = args[1:]
    if cmd == 'weather':
        if len(args) == 1 and args[0] in ['clear', 'rain', 'thunder']:
            try:
                await command("weather {}".format(args[0]))
            except:
                pass
    elif cmd == 'time':
        if len(args) == 1:
            if args[0] not in ['noon', 'day', 'night', 'midnight']:
                try:
                    val = int(args[0])
                except:
                    return
            try:
                await command("time set {}".format(args[0]))
            except:
                pass
    elif cmd == 'clear_arrow':
        try:
            await command("kill @e[type=arrow]")
        except:
            pass

async def log_sender(bot: Bot, log_file: TextIO) -> None:
    # get new logs.
    logs = log_file.readlines()
    text = ""
    for log in filter(log_filter, logs):
        line = log_mapper(log)
        try:
           await process_log_cmd(line)
        except Exception as e:
            pass
        text += line
    length = len(text)
    if length < 3 or length > 1024:
        log_file.seek(0, SEEK_END)
        return
    await bot.send_message(CHAT, text, disable_web_page_preview=True, disable_notification=True)


LOG_FILE_KEY = 'LOG_FILE'
LOG_FILE_INO_KEY = 'LOG_FILE_INO'


async def log_watch(context: ContextTypes.DEFAULT_TYPE) -> None:
    log_stat = os.stat(LOG_FILE_PATH)
    prev_log_ino: int | None = None
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
            await show_error_title(context.bot)
            logger.error("Error on sending logs", e)
        await sleep(1)

async def status_update(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if message is None:
        return
    new_chat_title = message.new_chat_title
    if not new_chat_title:
        return
    if context.chat_data is None:
        return
    key = 'chat_title_status_id'
    if key not in context.chat_data:
        context.chat_data[key] = message.message_id
        return
    prev_id = context.chat_data[key]
    try:
        await context.bot.delete_message(CHAT, prev_id)
    except error.BadRequest:
        pass
    context.chat_data[key] = message.message_id

_last_alarm_minute_key: tuple[int, int, int] | None = None


async def addict_alarm(context: ContextTypes.DEFAULT_TYPE) -> None:
    global _last_alarm_minute_key

    target_times = [(2, 0), (2, 30), (3, 0), (3, 30), (4, 0), (4, 30)]

    while True:
        now = datetime.now(timezone(timedelta(hours=8)))
        current_key = (now.toordinal(), now.hour, now.minute)

        if (now.hour, now.minute) in target_times:
            if _last_alarm_minute_key != current_key:
                try:
                    await command(
                        f"say [防沉迷温馨提示] 现在是东八区{now.hour}点{now.minute}分，"
                        f"已经是凌晨了，如果您居住在东八区、东九区，请注意健康喵~"
                    )
                    _last_alarm_minute_key = current_key
                except Exception as e:
                    logger.error(f"addict_alarm error: {e}")

        await sleep(30)


def main() -> None:
    """Start the bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(BOT_TOKEN).build()

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("list", list_command))
    application.add_handler(CommandHandler("allow", allow))
    application.add_handler(CommandHandler("time", set_time))
    application.add_handler(CommandHandler("weather", set_weather))
    application.add_handler(CommandHandler("whitelist", set_whitelist))
    application.add_handler(CommandHandler("clear_arrow", clear_arrow))

    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_TITLE, status_update))
    # on non command i.e message - echo the message on Telegram
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, forward_to_minecraft))

    job_queue = application.job_queue
    assert job_queue is not None
    job_queue.run_once(log_watch, when=4, name='log_watch')

    if TITLE != "":
        job_queue.run_once(edit_group_name, when=4)
    job_queue.run_once(addict_alarm, when=4)
    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
