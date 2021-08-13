#!/usr/bin/env python3
import logging
import os
import re
from os import environ, SEEK_END
from typing import TextIO

from dotenv import load_dotenv
from mcrcon import MCRcon, MCRconException

load_dotenv()
RCON_PASSWORD = environ.get("RCON_PASSWORD", "")

rcon = MCRcon("127.0.0.1", RCON_PASSWORD)

def command(s: str):
    rcon.connect()
    result = rcon.command(s)
    rcon.disconnect()
    return result


while True:
    print(command(input("> ")))
