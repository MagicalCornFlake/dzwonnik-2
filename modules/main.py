"""Dzwonnik 2, a Discord bot, by Konrad Guzek."""

PRELOADED_MODULES = set()


def init():
    # Standard library imports
    import asyncio
    import importlib
    import os
    from sys import modules

    global PRELOADED_MODULES

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

init()

# Local application imports
from . import bot, file_manager, util

def start_bot() -> bool:
    """Log in to the Discord bot and start its functionality.
    This function is blocking -- once the bot is connected, it will run until it's disconnected.

    Returns a boolean that indicates if the bot should be restarted.
    """
    # Save the previous log on startup
    file_manager.save_log_file()
    save_on_exit = True
    # # Update each imported module before starting the bot.
    # # The point of restarting the bot is to update the code without having to manually stop and start the script.
    reload()

    if __name__ == "__main__":
        file_manager.log("Started bot from main file! Assuming this is debug behaviour.")
    else:
        file_manager.log("Program starting...")
    try:
        file_manager.read_env_file()
        file_manager.read_data_file('data.json')
        event_loop = asyncio.get_event_loop()
        try:
            token = os.environ["BOT_TOKEN"]
        except KeyError:
            file_manager.log()
            file_manager.log("    --- CRITICAL ERROR! ---")
            file_manager.log("'BOT_TOKEN' OS environment variable not found. Program exiting.")
            save_on_exit = False
            # Do not restart bot
            return False
        else:
            # No problems finding OS variable containing bot token. Can login successfully.
            event_loop.run_until_complete(bot.client.login(token))
            file_manager.log("Bot logged in!")
        # Bot has been logged in, continue with attempt to connect
        try:
            # Blocking call:
            # The program will stay on this line until the bot is disconnected.
            file_manager.log("Connecting to Discord...")
            event_loop.run_until_complete(bot.client.connect())
        except KeyboardInterrupt:
            # Raised when the program is forcefully closed (eg. Ctrl+C in terminal).
            file_manager.log()
            file_manager.log("    --- Program manually closed by user (KeyboardInterrupt exception). ---")
            # Do not restart, since the closure of the bot was specifically requested by the user.
            return False
        else:
            # The bot was exited gracefully (eg. !exit, !restart command issued in Discord)
            file_manager.log()
            file_manager.log("    --- Bot execution terminated successfully. ---")
    finally:
        # Execute this no matter the circumstances, ensures data file is always up-to-date.
        if save_on_exit:
            # The file is saved before the start_bot() function returns.
            # Do not send a debug message since the bot is already offline.
            file_manager.save_data_file(should_log=False)
            file_manager.log("Successfully saved data file 'data.json'. Program exiting.")
    # By default, when the program is exited gracefully (see above), it is later restarted in 'run.pyw'.
    # If the user issues a command like !exit, !quit, the return_on_exit global variable is set to False,
    # and the bot is not restarted.
    return bot.restart_on_exit


if __name__ == "__main__":
    use_bot_testing = True
    start_bot()
