"""Module containing the code pertaining to the 'dumpfile' command."""

# Standard library imports
import json

# Third-party imports
from discord import Message

# Local application imports
from modules import bot, util

DESC = None


def read_file_contents(message: Message) -> str:
    """Command handler for the 'dumpfile' command."""
    args: list[str] = message.content.split(" ")
    try:
        filename = args[1]
        bot.send_log(f"Reading file '{filename}'...", force=True)
        # if not filename.endswith(".json"):
        #     raise FileNotFoundError
        with open(filename, "r", encoding="UTF-8") as file:
            try:
                contents = json.load(file)
            except json.JSONDecodeError:
                contents = file.read()
    except (IndexError, FileNotFoundError):
        if len(args) == 1:
            return "Należy podać nazwę pliku."
        return "Niepoprawna nazwa pliku."
    else:
        formatted_contents = util.format_code_results(contents)
        return "\n".join(formatted_contents)
