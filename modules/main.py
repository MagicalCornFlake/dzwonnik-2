"""Dzwonnik 2, a Discord bot, by Konrad Guzek."""

# Standard library imports
import asyncio
import importlib
import os

# Local application imports
from . import bot, file_manager, commands, util
from .commands import help, homework, steam_market
from .util.api import lucky_numbers as lucky_numbers_api, steam_market as steam_api
from .util.crawlers import lesson_plan as lesson_plan_crawler, substitutions as substitutions_crawler

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
    for module in (file_manager, commands, util, help, homework, steam_market, lucky_numbers_api, steam_api, lesson_plan_crawler, substitutions_crawler):
        importlib.reload(module)

    if __name__ == "__main__":
        file_manager.log("Started bot from main file! Assuming this is debug behaviour.")
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
