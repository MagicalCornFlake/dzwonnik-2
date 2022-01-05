#!/usr/bin/env python3
import importlib
from . import modules
from . modules import main


while True:
    importlib.reload(modules)
    importlib.reload(main)
    if not main.start_bot():
        # start_bot() returns a boolean indicating whether or not the bot should be restarted
        break
