"""Functionality for reading the .env files in the program root directory."""

# Standard library imports
import json
import os
import shutil
from datetime import datetime

# Local application imports
from . import bot, commands, util
from .util.api import lucky_numbers


CACHE_DIRECTORY = "cache"


on_exit_msg = {}


def read_data_file(filename: str = "data.json") -> None:
    """Reads data file and updates settings."""
    bot.send_log(f"Reading data file '{filename}'...", force=True)
    if not os.path.isfile(filename):
        data_file_404 = "Data file not found. Writing default values."
        bot.send_log(data_file_404, force=True)
        with open(filename, 'w', encoding="UTF-8") as file:
            default_settings = {
                "lesson_links": {},
                "homework_events": {},
                "tracked_market_items": [],
                "lucky_numbers": lucky_numbers.serialise()
            }
            json.dump(default_settings, file, indent=2)
    with open(filename, 'r', encoding="UTF-8") as file:
        data: dict[str, any] = json.load(file)
    # Read the lesson links data and update the local dictionary if it exists
    util.lesson_links.update(data.get("lesson_links", {}))
    # Read the on exit message saved in data file if it exists
    on_exit_msg.update(data.get("on_exit_msg", {}))
    # Creates new instances of the HomeworkEvent class with the data from the file
    new_event_candidates = commands.HomeworkEventContainer()
    for attributes in data.get("homework_events", {}).values():
        assert isinstance(attributes, dict)
        # Unpack the attributes and create a new homework event
        new_event_candidate = commands.HomeworkEvent(*attributes.values())
        new_event_candidates.append(new_event_candidate)
    commands.homework_events.remove_disjunction(new_event_candidates)
    for new_event_candidate in new_event_candidates:
        if new_event_candidate.serialised not in commands.homework_events.serialised:
            new_event_candidate.sort_into_container(commands.homework_events)

    for attributes in data.get("tracked_market_items", []):
        assert isinstance(attributes, dict)
        item = commands.TrackedItem(*attributes.values())
        if item not in commands.tracked_market_items:
            commands.tracked_market_items.append(item)

    lucky_numbers.cached_data = data.get("lucky_numbers", {})
    try:
        # Make datetime object from saved lucky numbers data
        date: str = data["lucky_numbers"]["date"]
        data_timestamp = datetime.strptime(date, "%Y-%m-%d")
    except (KeyError, TypeError, ValueError) as exception:
        # Saved lucky numbers data contains an invalid date; don't update cache
        bad_numbers = data["lucky_numbers"]
        bad_numbers = lucky_numbers.serialise(bad_numbers, pretty=True)
        fmt_exc = util.format_exception_info(exception)
        bad_lucky_numbers = f"Invalid lucky numbers:\n{bad_numbers}\nException trace:\n{fmt_exc}"
        bot.send_log(bad_lucky_numbers, force=True)
    else:
        lucky_numbers.cached_data["date"] = data_timestamp.date()
    bot.send_log(f"... successfully read data file '{filename}'.", force=True)


def save_data_file(filename: str = "data.json", allow_logs: bool = True) -> None:
    """Saves the settings stored in the program's memory to the file provided.

    Arguments:
        filename -- the name of the file relative to the program root directory to write to.
        Defaults to 'data.json'.
        allow_logs -- a boolean indicating whether or not the save should be logged.
    """
    if allow_logs:
        bot.send_log(f"Saving data file '{filename}'...", force=True)
    # Creates containers with the data to be saved in .json format
    serialised_homework_events = {
        event.id_string: event.serialised for event in commands.homework_events}
    serialised_tracked_market_items = [
        item.serialised for item in commands.tracked_market_items]
    # Creates a parent dictionary to save all data that needs to be saved
    data_to_be_saved = {
        "lesson_links": {code: link for code, link in util.lesson_links.items() if link},
        "homework_events": serialised_homework_events,
        "tracked_market_items": serialised_tracked_market_items,
        "lucky_numbers": lucky_numbers.serialise(),
        "on_exit_msg": on_exit_msg
    }

    # Format the data to be JSON-serialisable
    formatted_data: str = json.dumps(data_to_be_saved, indent=2)

    # Replaces file content with new data
    with open(filename, 'w', encoding="UTF-8") as file:
        file.write(formatted_data)

    # Sends a log with the formatted data
    if allow_logs:
        saved_file_msg = f"... successfully saved data file '{filename}'.\nData:\n{formatted_data}"
        bot.send_log(saved_file_msg, force=True)


def clear_log_file(filename: str) -> None:
    """Truncates the log file and writes to it a log header to identify when it was started."""
    formatted_time = f"{datetime.now():%Y-%m-%d @ %H.%M.%S}"
    log_template = f"START TIMESTAMP {formatted_time} END TIMESTAMP Started bot log.\n"
    with open(filename, 'w', encoding="UTF-8") as file:
        file.write(log_template)


def log(*raw_message: str) -> str:
    """Writes the message to the current log file, and returns the message formatted with the
    current time and proper indentation.
    """
    timestamp = f"{datetime.now():%Y-%m-%d @ %H:%M:%S}: "

    # Adds spaces after each newline so that the actual message is in line with the timestamp.
    message = timestamp + \
        ' '.join(map(str, raw_message)).replace(
            "\n", "\n" + " " * len(timestamp))
    with open("bot.log", 'a', encoding="UTF-8") as file:
        file.write(message + "\n")
    print(message)
    return message


def save_log_file() -> None:
    """Copies the active log file to a new file in the bot_logs directory and clears it."""
    try:
        with open("bot.log", 'r', encoding="UTF-8") as file:
            contents = file.read()
            if contents.startswith("START TIMESTAMP "):
                # Extract log creation date from active log
                log_start_time, log_contents = contents.lstrip(
                    "START TIMESTAMP ").split(" END TIMESTAMP ", maxsplit=1)
                log_start_time = log_start_time.rstrip('\n')
                # Copy active log contents to new file
                filename = f"bot_logs{os.path.sep}{log_start_time}.log"
                with open(filename, 'w', encoding="UTF-8") as file:
                    file.write(log_contents)
    except FileNotFoundError:
        # bot.log file does not exist
        pass
    clear_log_file("bot.log")


def read_cache(cache_name: str) -> dict:
    """Returns the cached data if it exists, otherwise an empty dictionary."""
    if not os.path.isdir(CACHE_DIRECTORY):
        os.mkdir(CACHE_DIRECTORY)
    filepath = f"{CACHE_DIRECTORY}/{cache_name}.json"
    if not os.path.isfile(filepath):
        return {}
    with open(filepath, 'r', encoding="UTF-8") as file:
        return json.load(file)


def get_cache(cache_name: str, force_update: bool, callback_function) -> tuple[dict, dict]:
    """Attempts to get the cache if it exists and the 'force_update' argument is set to False.

    If the above criteria are not met, the callback function is called and its return value
    is saved as the new cache.

    Arguments:
        cache_name -- the filename of the cache without the .json extension.
        force_update -- a boolean indicating if any existing caches should be updated forcefully.
        callback_function -- a lambda function that generates the new cache.

    Returns a tuple consisting of the cached data and the old cache (defaults to an empty dict).
    """
    cache = read_cache(cache_name)
    log(f"Cache for {cache_name} was {'*not* ' * (not cache)}found.")
    if not force_update and cache:
        # The cache has no need to be updated.
        return cache, cache
    old_cache = dict(cache)
    cache = callback_function()
    write_cache(cache_name, cache)
    write_cache(cache_name + "_old", old_cache)
    return cache, old_cache


def write_cache(cache_name: str, data: dict) -> None:
    """Serialises the given data and writes it in json format to the cache directory."""
    json_string = json.dumps(data, indent=2, ensure_ascii=False)
    with open(f"{CACHE_DIRECTORY}/{cache_name}.json", 'w', encoding="UTF-8") as file:
        file.write(json_string)


def clear_cache(cache_path: str = None) -> int:
    """Removes all files in the given directory, as well as the directory itself.

    Returns the number of removed files if the directory previously existed, otherwise False.
    """
    cache_path = cache_path or CACHE_DIRECTORY
    if os.path.exists(cache_path):
        files_removed = len(os.listdir(cache_path))
        shutil.rmtree(cache_path)
        log("Successfully cleared cache at directory: ./" + cache_path)
        return files_removed
    log(f"Error: The path './{cache_path}' does not exist.")
    return False


def read_env_file() -> bool:
    """Reads the .env file in the current directory and sets its contents in the program's memory.

    Returns a boolean indicating if any system environment variables were set as a result of this.
    """
    if not os.path.isfile(".env"):
        log("    --- '.env' file not found in program root directory. ---")
        return False
    return_value = False
    log()
    log("    --- Processing environment variable (.env) file... ---")
    with open('.env', 'r', encoding="UTF-8") as file:
        # Loop through each line in file
        for line in file.readlines():
            # Line does not contain a variable assignment
            if '=' not in line:
                continue
            # Extracts environment variable name and value from each line, stripping whitespaces.
            env_name, env_value = [
                s.strip() for s in line.rstrip('\n').split('=', maxsplit=1)]
            # Don't reassign value if already set in memory
            if env_name in os.environ:
                log(
                    f"Environment variable '{env_name}' is already set, ignoring .env assignment.")
                continue
            # Actually assign the environment variable value in memory
            os.environ[env_name] = env_value
            log(
                f"Set environment variable value '{env_name}' to '{env_value}'.")
            # Make the function return True since there was an env set
            return_value = True
    log("    --- Finished processing environment variable files. ---")
    log()
    return return_value
