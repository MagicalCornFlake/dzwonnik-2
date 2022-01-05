"""Functionality for reading the .env files in the program root directory."""

# Standard library imports
import json
import os
from datetime import datetime

# Local application imports
from . import bot, commands, util
from .util.api import lucky_numbers


def read_data_file(filename: str = "data.json") -> None:
    # Reads data file and updates settings
    if not os.path.isfile(filename):
        log("Data file not found. Writing default values.")
        with open(filename, 'w') as file:
            default_settings = {
                "lesson_links": {},
                "homework_events": {},
                "tracked_market_items": [],
                "lucky_numbers": lucky_numbers.serialise()
            }
            json.dump(default_settings, file, indent=2)
    with open(filename, 'r') as file:
        data: dict[str, any] = json.load(file)
    try:
        util.lesson_links.update(data.get("lesson_links", {}))
        log("Lesson links has been updated:", util.lesson_links)
    except KeyError:
        log("Lesson links not found in data file. Using blank values.")
    # Creates new instances of the HomeworkEvent class with the data from the file
    new_event_candidates = commands.HomeworkEventContainer()
    for event_id in data.get("homework_events", []):
        attributes = data["homework_events"][event_id]
        title, group, author_id, deadline, reminder_date, reminder_is_active = [
            attributes[attr] for attr in attributes]
        new_event_candidate = commands.HomeworkEvent(
            title, group, author_id, deadline, reminder_date, reminder_is_active)
        new_event_candidates.append(new_event_candidate)
    commands.homework_events.remove_disjunction(new_event_candidates)
    for new_event_candidate in new_event_candidates:
        if new_event_candidate.serialised not in commands.homework_events.serialised:
            new_event_candidate.sort_into_container(commands.homework_events)

    for attribs in data.get("tracked_market_items", []):
        item_attributes = [attribs[attrib] for attrib in attribs]
        item_name, min_price, max_price, author_id = item_attributes
        item = commands.TrackedItem(item_name, min_price, max_price, author_id)
        if item not in commands.tracked_market_items:
            commands.tracked_market_items.append(item)

    lucky_numbers.cached_data = data.get("lucky_numbers", {})
    try:
        # Make datetime object from saved lucky numbers data
        date: str = data["lucky_numbers"]["date"]
        data_timestamp = datetime.strptime(date, "%Y-%m-%d")
    except Exception as e:
        # Saved lucky numbers data contains an invalid date; don't update cache
        bot.send_log(f"Invalid lucky numbers:", data["lucky_numbers"])
        bot.send_log(util.format_exception_info(e))
    else:
        lucky_numbers.cached_data["date"] = data_timestamp.date()


def save_data_file(filename: str = "data.json", should_log: bool = True) -> None:
    """Saves the settings stored in the program's memory to the file provided.

    Arguments:
        filename -- the name of the file relative to the program root directory to write to (default 'data.json').
        should_log -- whether or not the save should be logged in the Discord Log and in the console.
    """
    if should_log:
        bot.send_log("Saving data file", filename)
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
        "lucky_numbers": lucky_numbers.serialise()
    }

    # Format the data to be JSON-serialisable
    formatted_data: str = json.dumps(data_to_be_saved, indent=2)

    # Replaces file content with new data
    with open(filename, 'w') as file:
        file.write(formatted_data)

    # Sends a log with the formatted data
    if should_log:
        bot.send_log(
            f"Successfully saved data file '{filename}'.\nData:\n{formatted_data}")


def clear_log_file(filename: str) -> None:
    """Truncates the given file and writes to it a log header to identify when the log was started."""
    with open(filename, 'w') as file:
        file.write(
            f"START TIMESTAMP {datetime.now():%Y-%m-%d @ %H.%M.%S} END TIMESTAMP Started bot log.\n")


def log(*raw_message: str) -> str:
    """Writes the message to the current log file, and returns the message formatted with the current time and proper indentation."""
    timestamp = f"{datetime.now():%Y-%m-%d @ %H:%M:%S}: "
    # Add spaces after each newline so that the actual message is in line to make up for the timestamp at the beginning
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
        with open("bot.log", 'r') as file:
            contents = file.read()
            if contents.startswith("START TIMESTAMP "):
                # Extract log creation date from active log
                log_start_time, log_contents = contents.lstrip(
                    "START TIMESTAMP ").split(" END TIMESTAMP ", maxsplit=1)
                log_start_time = log_start_time.rstrip('\n')
                # Copy active log contents to new file
                with open(f"bot_logs{os.path.sep}{log_start_time}.log", 'w') as file:
                    file.write(log_contents)
    except FileNotFoundError:
        # bot.log file does not exist
        pass
    clear_log_file("bot.log")


def cache_exists(cache_name: str) -> dict:
    """Returns the cached data if it exists, otherwise an empty dictionary."""
    filepath = f"cache/{cache_name}.json"
    if not os.path.isdir('cache'):
        os.mkdir('cache')
    if not os.path.isfile(filepath):
        return {}
    with open(filepath, 'r', encoding="UTF-8") as file:
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
    cache = cache_exists(cache_name)
    cache_existed = bool(cache)
    log(f"Cache for {cache_name} was {'not ' * (not cache_existed)}found.")
    if force_update or not cache_existed:
        cache = callback_function(force_update)
        json_string = json.dumps(cache, indent=4, ensure_ascii=False)
        with open(f"cache/{cache_name}.json", 'w', encoding="UTF-8") as file:
            file.write(json_string)
    return cache, cache_existed


def clear_cache(cache_path: str = "cache") -> bool:
    """Removes all files in the given directory, as well as the directory itself. Returns True if the directory previously existed, otherwise False."""
    if os.path.exists(cache_path):
        for filename in os.listdir(cache_path):
            os.remove(cache_path + os.path.sep + filename)
        os.rmdir(cache_path)
        log("Successfully cleared cache at directory: ./" + cache_path)
        return True
    else:
        log(
            f"Did not clear cache from directory ./{cache_path}: path does not exist.")
        return False


def read_env_file() -> bool:
    """Reads the .env file in the current directory and sets its contents in the program's local memory.
    Returns a boolean indicating if any system environment variables were set as a result of this.
    """
    if not os.path.isfile(".env"):
        log("    --- '.env' file not found in program root directory. ---")
        return False
    return_value = False
    log()
    log("    --- Processing environment variable (.env) file... ---")
    with open('.env', 'r') as file:
        # Loop through each line in file
        for line in file.readlines():
            # Line does not contain a variable assignment
            if '=' not in line:
                continue
            # Extract environment variable name and value from each line, stripping them from whitespaces
            env_name, env_value = [
                s.strip() for s in line.rstrip('\n').split('=', maxsplit=1)]
            # Don't reassign value if already set in memory
            if env_name in os.environ:
                log(
                    f"Environment variable '{env_name}' is already set, ignoring assignment in .env file.")
                continue
            # Actually assign the environment variable value in memory
            os.environ[env_name] = env_value
            log(
                f"Set environment variable value '{env_name}' to '{env_value}' in program local memory.")
            # Make the function return True since there was an env set
            return_value = True
    log("    --- Finished processing environment variable files. ---")
    log()
    return return_value
