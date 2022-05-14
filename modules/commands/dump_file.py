"""Module containing the code pertaining to the 'dumpfile' command."""

# Standard library imports
import json

# Third-party imports
from discord import Message

# Local application imports
from modules import bot, util

DESC = None

DEFAULT_FILENAME = "data.json"


def read_file_contents(message: Message) -> str:
    """Command handler for the 'dumpfile' command."""
    args: list[str] = message.content.split(" ")
    try:
        filename = args[1] if len(args) >= 2 else DEFAULT_FILENAME
        bot.send_log(f"Reading file '{filename}'...", force=True)
        # if not filename.endswith(".json"):
        #     raise FileNotFoundError
        with open(filename, "r", encoding="UTF-8") as file:
            contents = file.read()
            try:
                contents = json.loads(contents)
            except json.JSONDecodeError:
                pass
    except FileNotFoundError:
        return "Niepoprawna nazwa pliku."
    else:
        formatted_contents = util.format_code_results(contents)
        return "\n".join(formatted_contents)
