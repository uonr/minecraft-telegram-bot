#!/usr/bin/python3
import logging
import re
import threading
from os import environ, SEEK_END
from time import sleep
from typing import TextIO

import telegram
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from mcrcon import MCRcon

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
def start(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /start is issued."""
    update.message.reply_text('Hi!')


def help_command(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /help is issued."""
    update.message.reply_text('我现在主要是在 Telegram 和 Minecraft 之间转发。')


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


def forward_to_minecraft(update: Update, context: CallbackContext) -> None:
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
    if log.find("has made the advancement") != -1:
        return True
    elif log.find("[Async Chat Thread") != -1:
        return True
    elif log.find("] [Server thread/INFO]") == -1:
        return False
    elif log.find("lost connection") != -1:
        return False
    elif log.find("[Telegram]") != -1:
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
    if len(logs) == 0:
        log_file.seek(0, SEEK_END)
        return
    text = ""
    for log in filter(log_filter, logs):
        text += log_mapper(log)
    length = len(text)
    if length < 3 or length > 1024:
        return
    bot.send_message(CHAT, text, disable_web_page_preview=True, disable_notification=True)


def log_watch():
    bot = telegram.Bot(BOT_TOKEN, base_url=TELEGRAM_BOT_BASE_URL)
    log_file = open(LOG_FILE_PATH)
    log_file.seek(0, SEEK_END)
    while threading.main_thread().is_alive():
        if log_file.closed:
            log_file = open(LOG_FILE_PATH)
        log_sender(bot, log_file)
        sleep(0.5)


def main():
    rcon.connect()
    """Start the bot."""
    updater = Updater(BOT_TOKEN, base_url=TELEGRAM_BOT_BASE_URL)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(CommandHandler("time", set_time))

    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, forward_to_minecraft))
    threading.Thread(target=log_watch).start()

    updater.start_polling()

    updater.idle()
    rcon.disconnect()


if __name__ == '__main__':
    main()
