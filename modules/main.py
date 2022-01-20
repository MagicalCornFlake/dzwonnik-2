"""Dzwonnik 2, a Discord bot, by Konrad Guzek."""

# Standard library imports
import asyncio
import importlib
import os
import subprocess

# Local application imports
from . import bot, file_manager, util, commands


def start_bot() -> bool:
    """Log in to the Discord bot and start its functionality.
    This function is blocking -- once the bot is connected, it will run until it's disconnected.

    Returns a boolean that indicates if the bot should be restarted.
    """
    # Save the previous log on startup
    file_manager.save_active_log_file()
    file_manager.clear_log_file()
    save_on_exit = True

    for module in (bot, file_manager, util, commands):
        importlib.reload(module)
    if __name__ == "__main__":
        starting_msg = "Started bot from main file! Assuming this is debug behaviour."
    else:
        starting_msg = "Program starting..."
    bot.send_log(f"    --- {starting_msg} ---", force=True)
    file_manager.read_env_file()
    file_manager.read_data_file('data.json')
    event_loop = asyncio.get_event_loop()
    try:
        try:
            token = os.environ["BOT_TOKEN"]
        except KeyError:
            file_manager.log()
            file_manager.log("    --- CRITICAL ERROR! ---")
            env_404_msg = "'BOT_TOKEN' OS environment variable not found. Program exiting."
            file_manager.log(env_404_msg)
            save_on_exit = False
            # Do not restart bot
            return False
        else:
            # No problems finding OS variable containing bot token. Can login successfully.
            event_loop.run_until_complete(bot.client.login(token))
            bot.send_log("    --- Successfully authorised bot client! ---")
        # Bot has been logged in, continue with attempt to connect
        try:
            # Blocking call:
            # The program will stay on this line until the bot is disconnected.
            bot.send_log("    --- Connecting to Discord... ---")
            event_loop.run_until_complete(bot.client.connect())
        except KeyboardInterrupt:
            # Raised when the program is forcefully closed (e.g. Ctrl+C in terminal).
            exit_msg = "    --- Bot manually terminated by user (KeyboardInterrupt exception). ---"
            # Do not restart, since the closure of the bot was specifically requested by the user.
            return False
        else:
            # The bot was exited gracefully (e.g. !exit, !restart command issued in Discord)
            exit_msg = "    --- Bot execution terminated successfully. ---"
    finally:
        # Remove the python cache files so that the program does not cache the modules on restart.
        run_settings = {
            "capture_output": True,
            "text": True
        }
        result = subprocess.run(["pyclean", "."], check=False, **run_settings)
        file_manager.log(f"Pyclean: {result.stderr or result.stdout}")
        # Execute this in most cases; ensures data file is always up-to-date.
        if save_on_exit:
            # The file is saved before the start_bot() function returns.
            # Do not send a debug message since the bot is already offline.
            file_manager.save_data_file(allow_logs=False)
            saved_msg = "Successfully saved data file 'data.json'. Program exiting."
            file_manager.log(saved_msg)
        file_manager.log(exit_msg)
        file_manager.log()
    # By default, when the program is exited gracefully, it is later restarted in 'run.pyw'.
    # If the user issues a command like !exit, the return_on_exit global variable is set to False,
    # and the bot is not restarted.
    return bot.restart_on_exit


if __name__ == "__main__":
    bot.testing_channel = bot.ChannelID.BOT_TESTING
    start_bot()
