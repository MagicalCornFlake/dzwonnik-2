#!/usr/bin/env python3
# The above line marks the file as a script

from modules import main

restart_bot = main.start_bot()
while restart_bot:
    main.importlib.reload(main)
    restart_bot = main.start_bot()
