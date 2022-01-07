"""__init__.py file for the web utility-related modules."""

# Standard library imports
import traceback
from datetime import datetime


OUR_CLASS = "2d"

lesson_plan: dict[str, any] = {}
lesson_links: dict[str, str] = {}

# Used to show the current lesson in the lesson plan (e.g. '!plan' command).
current_period: int = -1


def format_class(class_name: str = None):
    """Change the format of the class name string using roman numerals instead of arabic numerals.
    Also capitalises the class letter.

    E.g. '2d' -> 'IID'

    Arguments:
        class_name -- the name of the class. Defaults to the value of the `our_class` variable."""
    class_name = class_name or OUR_CLASS
    if len(class_name) < 2:
        err_msg = f"Invalid class name: '{class_name}' is too short (min. 2 characters)."
        raise ValueError(err_msg)
    try:
        formatted = 'I' * int(class_name[0])
    except ValueError:
        err_msg = f"Invalid class name: '{class_name}' does not start with a number."
        raise ValueError(err_msg) from None
    else:
        return formatted + class_name[1:].upper()


def format_exception_info(exception: Exception):
    """Returns the exception stack trace in the form of a string as it is displayed in the shell.

    Arguments:
        exception -- the exception to format.
    """
    info = type(exception), exception, exception.__traceback__
    fmt_info = traceback.format_exception(*info)
    return ''.join(fmt_info)


def conjugate_numeric(num: int, word: str) -> str:
    """Inputs a number and base noun and returns the correctly conjugated string in Polish.

    Arguments:
        num -- the quantity, integer
        word -- the base noun, e.g. 'godzin' or 'minut'
    """
    if num == 1:
        suffix = "ę"
    else:
        last_digit: int = int(str(num)[-1])
        suffix = "y" if 1 < last_digit < 5 and num not in [12, 13, 14] else ""
    return f"{num} {word}{suffix}"


def get_time(period: int, base_time: datetime, get_period_end_time: bool) -> tuple[str, datetime]:
    times = lesson_plan["Godz"][period]
    hour, minute = times[get_period_end_time]
    replace_args = {
        "hour": hour,
        "minute": minute,
        "second": 0,
        "microsecond": 0
    }
    date_time = base_time.replace(**replace_args)
    return date_time


def get_lesson_name(lesson_code: str) -> str:
    # Mappings contain a boolean indicating if the entire word should be mapped or only if it starts with the phrase
    mappings: dict[str, tuple[bool, str]] = {
        "zaj.z-wych.": (False, "zajęcia z wychowawcą"),
        "WF": (False, "wychowanie fizyczne"),
        "WOS": (False, "wiedza o społeczeństwie"),
        "TOK": (False, "theory of knowledge"),
        "j.": (False, "język "),
        "hiszp.": (True, "hiszpański"),
        "ang.": (True, "angielski"),
        "przedsięb.": (True, "przedsiębiorczość")
    }
    # Remove trailing '.' and leading 'r-'
    lesson_name = lesson_code[2 * lesson_code.startswith('r-'):]
    for abbreviation, behaviour in mappings.items():
        map_entire_word, mapping = behaviour
        if map_entire_word or lesson_name.startswith(abbreviation):
            lesson_name = lesson_name.replace(abbreviation, mapping)
    # Handle edge cases
    if lesson_code in ["mat", "r-mat"]:
        lesson_name += "ematyka"
    return lesson_name + " rozszerzona" * lesson_code.startswith('r-')


def get_lesson_link(lesson_code: str) -> str:
    if lesson_code not in lesson_links:
        lesson_links[lesson_code] = None
    return lesson_links[lesson_code]


def get_formatted_period_time(period: int or str = None) -> str:
    """Get a string representing the start and end times for a given period, according to the lesson plan.
    e.g. [[8, 0], [8, 45]] -> "08:00-08:45

    Arguments:
        period -- the period to get the times for. Defaults to the current period.
    """
    times: list[list[int]] = lesson_plan["Godz"][int(period or current_period)]
    return "-".join([':'.join([f"{t:02}" for t in time]) for time in times])
