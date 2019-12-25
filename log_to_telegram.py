#!/usr/bin/env python
# -*- coding: utf-8 -*-
import re
import logging
import telegram
from time import sleep
from typing import Optional
from os import environ
from os.path import getmtime
from dotenv import load_dotenv

load_dotenv()
# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)
bot = telegram.Bot(environ["BOT_TOKEN"])
LOG_FILE_PATH = environ["LOG_FILE_PATH"]
CHAT = int(environ["CHAT_ID"])


LAST_MODIFIED: float = 0.0
LAST_LOG: Optional[str] = None


def log_filter(log: str) -> bool:
    if log.find("[Async Chat Thread") != -1:
        return True
    if log.find("] [Server thread/INFO]") == -1:
        return False
    if log.find("lost connection") != -1 or log.find("has made the advancement") != -1:
        return False
    return True


IP_MATCH = re.compile(r"\[\/\d+\.\d+\.\d+\.\d+:\d+\]")
HEAD_MATCH = re.compile(r"^\[\d+:\d+:\d+\] \[[^\]]+\]:\s+")


def log_sender():
    global LAST_LOG
    global LAST_MODIFIED
    modified = getmtime(LOG_FILE_PATH)
    if modified <= LAST_MODIFIED:
        return
    LAST_MODIFIED = modified
    with open(LOG_FILE_PATH) as log_file:
        logs = log_file.readlines()
        # compare the last log.
        if LAST_LOG:
            try:
                last_log_index = logs.index(LAST_LOG)
            except ValueError:
                pass
            else:
                logs = logs[last_log_index + 1:]
                if len(logs) == 0:
                    return
        LAST_LOG = logs[-1]  # update the last log.
        text = ""
        for log in filter(log_filter, logs):
            # some processing.
            log = HEAD_MATCH.sub("", log)
            log = IP_MATCH.sub("", log)
            log = log.replace("[m", "")

            text += log
        length = len(text)
        if length < 3 or length > 1024:
            return
        try:
            bot.send_message(CHAT, text, disable_web_page_preview=True, disable_notification=True)
        except telegram.error.TimedOut:
            pass


def main():
    while True:
        try:
            log_sender()
        except:
            logger.exception("unknown error")
        sleep(1)


if __name__ == '__main__':
    main()
