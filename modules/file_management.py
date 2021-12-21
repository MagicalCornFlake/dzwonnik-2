"""Functionality for reading the .env files in the program root directory."""
import os
from datetime import datetime


def clear_log_file(filename: str) -> None:
    with open(filename, 'w') as file:
        file.write(f"{datetime.now():%Y-%m-%d @ %H.%M.%S} END TIMESTAMP Started bot log.\n")


def write_log(message: str) -> None:
    with open("bot.log", 'a') as file:
        file.write(f"{datetime.now():%Y-%m-%d @ %H:%M:%S}: {message}\n")


def save_log_file() -> None:
    try:
        with open("bot.log", 'r') as file:
            log_start_time, log_contents = file.read().split(" END TIMESTAMP ", maxsplit=1)
    except ValueError:
        # Discard current log
        pass
    else:
        with open("bot_logs" + os.path.sep + log_start_time.rstrip("\n") + ".log", 'w') as file:
            file.write(log_contents)
    clear_log_file("bot.log")


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
    write_log("\n    --- Processing environment variable (.env) files... ---")
    return_value = False
    for filename in os.listdir():
        if not filename.endswith('.env'):
            continue
        env_name = filename.rstrip('.env')
        if env_name in os.environ:
            write_log(f"Environment variable '{env_name}' is already set, ignoring the .env file.")
            continue
        return_value = True
        with open(filename, 'r') as file:
            env_value = file.read().rstrip('\n')
            os.environ[env_name] = env_value
            write_log(f"Set environment variable value '{env_name}' to '{env_value}' in program local memory.")
    # Newline for readability
    write_log("    --- Finished processing environment variable files. ---\n")
    return return_value
