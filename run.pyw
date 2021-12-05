#!/usr/bin/env python3
# Above line marks file as script

from modules import main

restart_bot = main.start_bot()
while restart_bot:
    main.importlib.reload(main)
    restart_bot = main.start_bot()
