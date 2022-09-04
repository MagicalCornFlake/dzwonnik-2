"""Functionality for reading and saving the bot's data file."""

# Standard library imports
import json
import os
from datetime import datetime

# Third-party imports
from corny_commons import util as ccutil

# Local application imports
from modules import bot, commands, util
from modules.api import lucky_numbers

DATA_IDENTICAL_MSG = "... data is identical; no changes have been made."


on_exit_msg = {}
last_substitutions = {}


def read_data_file(filename: str = "data.json") -> None:
    """Reads data file and updates settings."""
    bot.send_log(f"Reading data file '{filename}'...", force=True)
    if not os.path.isfile(filename):
        data_file_404 = "Data file not found. Writing default values."
        bot.send_log(data_file_404, force=True)
        with open(filename, "w", encoding="UTF-8") as file:
            default_settings = {
                "lesson_links": {},
                "homework_events": {},
                "tracked_market_items": [],
                "lucky_numbers": lucky_numbers.serialise(),
            }
            json.dump(default_settings, file, indent=2)
    with open(filename, "r", encoding="UTF-8") as file:
        data: dict[str, any] = json.load(file)
    # Read the lesson links data and update the local dictionary if it exists
    util.lesson_links.update(data.get("lesson_links", {}))
    # Read the on exit message saved in data file if it exists
    on_exit_msg.update(data.get("on_exit_msg", {}))
    # Read the last substitutions info saved in data file if it exists
    last_substitutions.update(data.get("last_substitutions", {}))
    # Creates new instances of the HomeworkEvent class with the data from the file
    new_event_candidates = commands.HomeworkEventContainer()
    for attributes in data.get("homework_events", {}).values():
        assert isinstance(attributes, dict)
        # Unpack the attributes and create a new homework event
        new_event_candidate = commands.HomeworkEvent(*attributes.values())
        new_event_candidates.append(new_event_candidate)
    commands.homework.homework_events.remove_disjunction(new_event_candidates)
    for new_event_candidate in new_event_candidates:
        if (
            new_event_candidate.serialised
            not in commands.homework.homework_events.serialised
        ):
            new_event_candidate.sort_into_container(commands.homework.homework_events)

    for attributes in data.get("tracked_market_items", []):
        assert isinstance(attributes, dict)
        item = commands.TrackedItem(*attributes.values())
        if item not in commands.steam_market.tracked_market_items:
            commands.steam_market.tracked_market_items.append(item)

    lucky_numbers.cached_data = data.get("lucky_numbers", {})
    try:
        # Make datetime object from saved lucky numbers data
        date: str = data["lucky_numbers"]["date"]
        data_timestamp = datetime.strptime(date, "%Y-%m-%d")
    except (KeyError, TypeError, ValueError) as exception:
        # Saved lucky numbers data contains an invalid date; don't update cache
        bad_numbers = data["lucky_numbers"]
        bad_numbers = lucky_numbers.serialise(bad_numbers, pretty=True)
        fmt_exc = ccutil.format_exception_info(exception)
        bad_lucky_numbers = (
            f"Invalid lucky numbers:\n{bad_numbers}\nException trace:\n{fmt_exc}"
        )
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
        event.id_string: event.serialised for event in commands.homework.homework_events
    }
    serialised_tracked_market_items = [
        item.serialised for item in commands.steam_market.tracked_market_items
    ]
    # Creates a parent dictionary to save all data that needs to be saved
    data_to_be_saved = {
        "lesson_links": {
            code: link for code, link in util.lesson_links.items() if link
        },
        "homework_events": serialised_homework_events,
        "tracked_market_items": serialised_tracked_market_items,
        "lucky_numbers": lucky_numbers.serialise(),
        "on_exit_msg": on_exit_msg,
        "last_substitutions": last_substitutions,
    }
    # Checks if the data actually needs to be saved
    with open(filename, "r", encoding="UTF-8") as file:
        existing_data = json.load(file)
    if existing_data == data_to_be_saved:
        if allow_logs:
            bot.send_log(DATA_IDENTICAL_MSG, force=True)
        return

    # Format the data to be JSON-serialisable
    formatted_data: str = json.dumps(data_to_be_saved, indent=2)

    # Replaces file content with new data
    with open(filename, "w", encoding="UTF-8") as file:
        file.write(formatted_data)

    # Sends a log with the formatted data
    if allow_logs:
        bot.send_log(f"... successfully saved data file '{filename}'.", force=True)
        bot.send_log(formatted_data)
