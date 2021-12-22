"""Functionality for reading the .env files in the program root directory."""
import json
import os
from datetime import datetime


def clear_log_file(filename: str) -> None:
    """Truncates the given file and writes to it a log header to identify when the log was started."""
    with open(filename, 'w') as file:
        file.write(f"START TIMESTAMP {datetime.now():%Y-%m-%d @ %H.%M.%S} END TIMESTAMP Started bot log.\n")


def log(*raw_message: str) -> str:
    """Writes the message to the current log file, and returns the message formatted with the current time and proper indentation."""
    timestamp = f"{datetime.now():%Y-%m-%d @ %H:%M:%S}: "
    # Add spaces after each newline so that the actual message is in line to make up for the timestamp at the beginning 
    message = timestamp + ' '.join(map(str, raw_message)).replace("\n", "\n" + " " * len(timestamp))
    with open("bot.log", 'a') as file:

        file.write(message + "\n")
    return message


def save_log_file() -> None:
    """Copies the active log file to a new file in the bot_logs directory and clears it."""
    with open("bot.log", 'r') as file:
        contents = file.read()
        if contents.startswith("START TIMESTAMP "):
            # Extract log creation date from active log
            log_start_time, log_contents = contents.lstrip("START TIMESTAMP ").split(" END TIMESTAMP ", maxsplit=1)
            # Copy active log contents to new file
            with open("bot_logs" + os.path.sep + log_start_time.rstrip("\n") + ".log", 'w') as file:
                file.write(log_contents)
    clear_log_file("bot.log")


def check_if_cache_exists(cache_name: str) -> dict:
    """Returns the cached data if it exists, otherwise an empty dictionary."""
    filepath = f"cache/{cache_name}.json"    
    if not os.path.isdir('cache'):
        os.mkdir('cache')
    if not os.path.isfile(filepath):
        return {}
    with open(filepath, 'r') as file:
        return json.load(file)


def get_cache(cache_name: str, force_update: bool, callback_function) -> tuple[bool, dict]:
    """Attempts to get the cache if it exists and the 'force_update' argument is set to False.
    If the above criterion are not met, the callback function is called and its return value is saved as the new cache.
    Returns the cached data and a boolean indicating if it previously existed.

    Arguments:
        cache_name -- the filename of the cache without the .json extension.
        force_update -- a boolean indicating if the cache should be forcefully updated even if it already exists.
        callback_function -- a lambda function that takes 'force_update' as an argument and returns the new cache.
    """
    cache = check_if_cache_exists(cache_name)
    cache_exists = bool(cache)
    if force_update or not cache_exists:
        cache = callback_function(force_update)
        json_string = json.dumps(cache, indent=4, ensure_ascii=False)
        log("Updated cache:\n", )
        with open(f"cache/{cache_name}.json", 'w') as file:
            file.write(json_string)
    return cache, cache_exists


def clear_cache(cache_path: str = "cache") -> bool:
    """Removes all files in the given directory, as well as the directory itself. Returns True if the directory previously existed, otherwise False."""
    if os.path.exists(cache_path):
        for filename in os.listdir(cache_path):
            os.remove(cache_path + os.path.sep + filename)
        os.rmdir(cache_path)
        print("Successfully cleared cache at directory: ./" + cache_path)
        return True
    else:
        print(f"Did not clear cache from directory ./{cache_path}: path does not exist.")
        return False


def read_env_files() -> bool:
    """Reads the .env files in the current directory and sets their contents in the program's local memory.
    Returns a boolean indicating if any system environment variables were set as a result of this.
    """
    log("\n    --- Processing environment variable (.env) files... ---")
    return_value = False
    for filename in os.listdir():
        if not filename.endswith('.env'):
            continue
        env_name = filename.rstrip('.env')
        if env_name in os.environ:
            log(f"Environment variable '{env_name}' is already set, ignoring the .env file.")
            continue
        return_value = True
        with open(filename, 'r') as file:
            env_value = file.read().rstrip('\n')
            os.environ[env_name] = env_value
            log(f"Set environment variable value '{env_name}' to '{env_value}' in program local memory.")
    # Newline for readability
    log("    --- Finished processing environment variable files. ---\n")
    return return_value
