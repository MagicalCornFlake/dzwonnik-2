"""__init__.py file for the web utility-related modules."""

# Standard library imports
from traceback import format_exception
from datetime import datetime


lesson_plan: dict[str, list[int] or list[list[int]] or list[list[dict[str, str]]]] = {}
lesson_links: dict[str, str] = {}


def format_exception_info(e: Exception):
    return ''.join(format_exception(type(e), e, e.__traceback__))


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
    date_time = base_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
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
    # Handle edge cases
    if lesson_code in ["mat", "r-mat"]:
        return "matematyka rozszerzona"
    if lesson_code == "mat.":
        return "matematyka"
    # Remove trailing '.' and leading 'r-'
    lesson_name = lesson_code[2 * lesson_code.startswith('r-'):]
    for abbreviation, behaviour in mappings.items():
        map_entire_word, mapping = behaviour
        if map_entire_word or lesson_name.startswith(abbreviation):
            lesson_name = lesson_name.replace(abbreviation, mapping)
    return lesson_name + " rozszerzona" * lesson_code.startswith('r-')


def get_lesson_link(lesson_code: str) -> str:
    if lesson_code not in lesson_links:
        lesson_links[lesson_code] = None
    return lesson_links[lesson_code]


def get_formatted_period_time(period: int) -> str:
    """Get a string representing the start and end times for a given period, according to the lesson plan.
    e.g. [[8, 0], [8, 45]] -> "08:00-08:45
    """
    times: list[list[int]] = lesson_plan["Godz"][period]
    return "-".join([':'.join([f"{t:02}" for t in time]) for time in times])
