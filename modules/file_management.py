"""Functionality for reading the .env files in the program root directory."""
import os
from datetime import datetime

files_in_pwd = []


def clear_log_files() -> None:
    for filename in files_in_pwd:
        if filename.endswith('.log'):
            with open(filename, 'w') as file:
                file.write(f"{datetime.now():%Y-%m-%d @ %H.%M.%S} END TIMESTAMP ")
                file.write("Started bot log.\n")


def save_log_file() -> None:
    with open("bot.log", 'r') as file:
        log_start_time, log_contents = file.read().split(" END TIMESTAMP ", maxsplit=1)
    with open("bot_logs" + os.path.sep + log_start_time.rstrip("\n\r") + ".log", 'w') as file:
        file.write(log_contents)


def read_env_files() -> bool:
    print("\n    --- Processing environment variable (.env) files... ---")
    return_value = False
    for filename in os.listdir():
        files_in_pwd.append(filename)
        if not filename.endswith('.env'):
            continue
        env_name = filename.rstrip('.env')
        if env_name in os.environ:
            print(f"Environment variable '{env_name}' is already set, ignoring the .env file.")
            continue
        return_value = True
        with open(filename, 'r') as file:
            env_value = file.read().rstrip('\n\r')
            os.environ[env_name] = env_value
            print(f"Set environment variable value '{env_name}' to '{env_value}' in program local memory.")
    # Newline for readability
    print("    --- Finished processing environment variable files. ---\n")
    return return_value
