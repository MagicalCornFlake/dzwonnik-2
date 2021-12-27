#!/usr/bin/env python3
# The above line marks the file as a script


# Standard library imports
import importlib
from sys import modules

# sys and importlib are ignored here too
PRELOADED_MODULES = set(modules.values())


def reload() :
    from sys import modules
    import importlib

    for module in set(modules.values()) - PRELOADED_MODULES:
        try:
            importlib.reload(module)
        except:
            # there are some problems that are swept under the rug here
            pass


from modules import main


while True:
    reload()
    if not main.start_bot():
        # function start_bot() returns a boolean indicating whether or not the bot should be restarted
        break
