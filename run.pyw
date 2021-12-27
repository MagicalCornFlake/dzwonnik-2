#!/usr/bin/env python3
# The above line marks the file as a script

from modules import main

while True:
    main.importlib.reload(main)
    if not main.start_bot():
        # function start_bot() returns a boolean indicating whether or not the bot should be restarted
        break
