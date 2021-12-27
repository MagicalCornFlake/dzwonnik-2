"""__init__.py file for the web utility-related modules."""

# Standard library imports
import asyncio
from traceback import format_exception
from datetime import datetime

# Third-party imports
from discord import Intents, Client

# Local application imports
from . import web_api
from api import steam_api
from crawlers import plan_crawler
from .. import weekday_names, enable_log_messages, file_manager, ChannelID


intents = Intents.default()
intents.members = True
client = Client(intents=intents)
lesson_plan: dict[str, list[int] or list[list[int]] or list[list[dict[str, str]]]] = {}
lesson_links: dict[str, str] = {}


def initialise_variables():
    global lesson_plan, lesson_links
    lesson_plan = plan_crawler.get_lesson_plan(force_update=True)[0]
    lesson_names: set[str] = set()
    for weekday in [key for key in lesson_plan.keys() if key in weekday_names]:
        for period in lesson_plan[weekday]:
            for lesson in period:
                lesson_names.add(lesson["name"])
    for lesson in sorted(lesson_names):
        lesson_links[lesson] = None


def log(*message) -> None:
    """Shorthand for sending a message to the log channel and program output file regardless of log settings."""
    send_log(*message, force=True)


def send_log(*raw_message, force=False) -> None:
    """Determine if the message should actually be logged, and if so, generate the string that should be sent."""
    if not (enable_log_messages or force):
        return
    
    msg = file_manager.log(*raw_message)
    log_loop = asyncio.get_event_loop()
    log_loop.create_task(send_log_message(msg if len(msg) <= 4000 else f"Log message too long ({len(msg)} characters). Check 'bot.log' file."))


async def send_log_message(message) -> None:
    log_channel = client.get_channel(ChannelID.bot_logs)
    await client.wait_until_ready()
    await log_channel.send(f"```py\n{message}\n```")


def format_exception(e: Exception):
    return ''.join(format_exception(type(e), e, e.__traceback__))


def get_web_api_error_message(e: Exception) -> str:
    if type(e) is web_api.InvalidResponseException:
        return f"Nastąpił błąd w połączeniu: {e.status_code}"
    if type(e) is web_api.TooManyRequestsException:
        return f"Musisz poczekać jeszcze {web_api.max_request_cooldown - e.time_since_last_request:.2f}s."
    if type(e) is steam_api.NoSuchItemException:
        return f":x: Nie znaleziono przedmiotu `{e.query}`. Spróbuj ponownie i upewnij się, że nazwa się zgadza."
    else:
        raise e


def conjugate_numeric(num: int, word: str) -> str:
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
    mappings: dict[str, tuple[bool, str]] = {
        "zaj.z-wych": (False, "zajęcia z wychowawcą"),
        "WF": (False, "wychowanie fizyczne"),
        "WOS": (False, "wiedza o społeczeństwie"),
        "TOK": (False, "theory of knowledge"),
        "mat": (False, "matematyka"),
        "j.": (False, "język "),
        "hiszp": (True, "hiszpański"),
        "ang": (True, "angielski"),
        "przedsięb": (True, "przedsiębiorczość")
    }
    lesson_name = lesson_code.rstrip('.')[2 * lesson_code.startswith('r-'):]
    for abbreviation, behaviour in mappings.items():
        map_entire_word, mapping = behaviour
        if map_entire_word or lesson_name.startswith(abbreviation):
            lesson_name = lesson_name.replace(abbreviation, mapping)
    return lesson_name + " rozszerzona" * lesson_code.startswith('r-')


def get_lesson_link(lesson_code: str) -> str:
    try:
        return lesson_links[lesson_code]
    except KeyError:
        return None


def get_formatted_period_time(period: int) -> str:
    times: list[list[int]] = lesson_plan["Godz"][period]
    # e.g. [[8, 0], [8, 45]] -> "08:00-08:45"
    return "-".join([':'.join([f"{t:02}" for t in time]) for time in times])
