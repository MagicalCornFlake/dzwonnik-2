"""Module containing general-purpose utility functions."""

# Standard library imports
from datetime import datetime
import json

# Third-party imports
from corny_commons.util import web

# Local application imports
from modules import GROUP_NAMES
# from modules.commands import URL_404 TODO: revert

URL_404 = "https://www.example.com/"
OUR_CLASS = "2d"

lesson_plan: dict[str, any] = {}
lesson_links: dict[str, str] = {}

# Used to show the current lesson in the lesson plan (e.g. '!plan' command).
current_period: int = -1
next_period: int = -1


class ExecResultList(list):
    """Defines a custom class that derives from the `list` base type.

    This class redefines the += operator to append new items rather than merge lists.
    """

    def __init__(self):
        super().__init__(self)

    def __iadd__(self, __x):
        """Appends an item to the list."""
        self.append(__x)
        return self


def format_class(class_name: str = None, reverse: bool = False):
    """Change the format of the class name string using roman numerals instead of arabic numerals.
    Also capitalises the class letter.
    The behaviour can be reversed using the `reverse` argument.

    E.g. '2d' -> 'IID'

    Arguments:
        `class_name` -- the name of the class. Defaults to the value of the `our_class` variable.

        `reverse` -- if True, the class name will be converted from roman numerals into arabic
        numerals. E.g. 'IID' -> '2d'.
    """
    if reverse:
        class_name = (class_name or format_class()).upper()
        class_num = class_name.count("I")
        return f"{class_num}{class_name[class_num:].lower()}"
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


def get_time(period: int, base_time: datetime, get_period_end_time: bool) -> tuple[str, datetime]:
    """Returns a datetime on the same day of `base_time` with the time corresponding to the
    start (or end) time of the given period.

    Arguments:
        period: an integer representing the number of the period.
        base_time: the base datetime that will be used to construct the returned value.
        get_period_end_time: if this is true, the period's end time will be used.
    """
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
    """Returns a lesson's name from its code."""
    # The boolean indicates if the word should only be mapped if it starts with the given phrase.
    mappings: dict[str, str] = {
        "zaj.z-wych.": (False, "zajęcia z wychowawcą"),
        "wf": (False, "wychowanie fizyczne"),
        "wos": (False, "wiedza o społeczeństwie"),
        "tok": (False, "theory of knowledge"),
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
    if lesson_code.startswith("r-"):
        # Determine the grammatical gender of the subject name
        if lesson_name.endswith("a"):
            # Feminine (most subjects)
            suffix = "a"
        else:
            # Masculine (in this case probably only the acronyms, e.g. WF, WOS, EDB, TOK)
            suffix = "y"
        lesson_name += " rozszerzon" + suffix
    return lesson_name


def get_lesson_link(lesson_code: str) -> str:
    """Returns the lesson link corresponding to the given lesson. If lesson_links does not contain
    data for the lesson, assigns its link to None and returns that.

    Arguments:
        lesson_code -- a string containing the code of the lesson."""
    lesson_code = lesson_code.lower()
    if lesson_code not in lesson_links:
        lesson_links[lesson_code] = None
    return lesson_links[lesson_code]


def format_lesson_info(lesson: dict[str, str], add_links: bool = False) -> str:
    """Formats the lesson object into a string representation of it."""
    lesson_name = get_lesson_name(lesson['name'])
    room = lesson['room_id']

    lesson_info: str = f"{lesson_name} - sala {room}"
    if add_links:
        # Stylise the lesson info as a hyperlink to the Google Meet lesson
        raw_link = get_lesson_link(lesson['name'])
        link = f"https://meet.google.com/{raw_link}" if raw_link else URL_404
        lesson_info = f"[{lesson_info}]({link})"

    if lesson['group'] != "grupa_0":
        group_name = GROUP_NAMES.get(lesson['group'], lesson['group'])
        lesson_info += f" ({group_name})"
    return lesson_info


def get_formatted_period_time(period: int or str = None) -> str:
    """Returns a string representing the start and end times of a given period in the lesson plan.
    e.g. ((8, 0), (8, 45)) -> "08:00-08:45

    Arguments:
        period -- the period to get the times for. Defaults to the current period.
    """
    times: list[list[int]] = lesson_plan["Godz"][int(period or current_period)]
    return "-".join([':'.join([f"{t:02}" for t in time]) for time in times])


def get_error_message(web_exc: web.WebException) -> str:
    """Returns the error message to be displayed to the user if a web exception occurs."""
    if not isinstance(web_exc, web.WebException):
        raise web_exc from TypeError
    if isinstance(web_exc, web.InvalidResponseException):
        return f"Nastąpił błąd w połączeniu: {web_exc.status_code}"
    if isinstance(web_exc, web.TooManyRequestsException):
        return f"Musisz poczekać jeszcze {web_exc.cooldown}s."
    # The exception must be .api.steam_market.NoSuchItemException
    return (f":x: Nie znaleziono przedmiotu `{web_exc.query}`. "
            f"Spróbuj ponownie i upewnij się, że nazwa się zgadza.")


def format_code_results(code_results: ExecResultList or any) -> ExecResultList:
    """Formats returned Python expressions as strings or JSON using Discord markdown formatting."""
    results = []
    json_result_indices = []
    for res in code_results if isinstance(code_results, ExecResultList) else [code_results]:
        json_result_indices.append("")
        if type(res) in [list, dict, tuple]:
            try:
                # Add the index of the current result to the list of JSON result indices
                json_result_indices.append(len(results))

                tmp = json.dumps(res, indent=2, ensure_ascii=False)
                results.append(tmp)
            except (TypeError, OverflowError):
                pass
            else:
                continue
        results.append(str(res))

    # Format the results using Discord formatting
    formatted_results = ExecResultList()

    for index, result in enumerate(results):
        if index in json_result_indices:
            formatted_results += f"```json\n{result}```"
        else:
            formatted_results += f"```py\n{str(result) or 'None'}```"
    return formatted_results
