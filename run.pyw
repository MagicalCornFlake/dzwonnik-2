#!/usr/bin/env python3
import importlib
from modules import main


while True:
    importlib.reload(main)
    if not main.start_bot():
        # start_bot() returns a boolean indicating whether or not the bot should be restarted
        break
