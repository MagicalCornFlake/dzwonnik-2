"""Module containing code relating to the 'nb' command."""

# Standard library imports
from datetime import datetime
from math import ceil

# Third-party imports
from discord import Message
from corny_commons.util import polish

# Local application imports
from modules import bot, util, Emoji
from modules.commands import get_datetime_from_input, get_lesson_by_roles, get_next_period


DESC = """Mówi kiedy jest następna przerwa.
    Parametry: __godzina__, __minuta__
    Przykład: `{p}nb 9 30` - wyświetliłaby się najbliższa przerwa po godzinie 09:30.
    *Domyślnie pokazana jest najbliższa przerwa od aktualnego czasu*"""


def get_next_break(message: Message) -> str:
    """Event handler for the 'nb' command."""
    time = get_datetime_from_input(message, 'nb')
    if not isinstance(time, datetime):
        # The get_datetime_from_input() function returned an error message
        return time

    next_period_is_today, lesson_period = get_next_period(time)[:2]

    if next_period_is_today:
        lesson = get_lesson_by_roles(lesson_period % 10, time.weekday(), message.author.roles)
        if not lesson:
            return f"{Emoji.INFO} Dzisiaj już nie ma dla Ciebie żadnych lekcji!"
        break_start_datetime = util.get_time(lesson['period'], time, True)
        break_countdown = break_start_datetime - time
        mins = ceil(break_countdown.seconds / 60)
        hours = (polish.conjugate_numeric(mins // 60, 'godzin') + " ") * (mins >= 60)
        minutes = f"{polish.conjugate_numeric(mins % 60, 'minut')}"
        break_time_str = util.get_formatted_period_time(lesson['period']).split('-')[1]
        msg = f"{Emoji.INFO} Następna przerwa jest za {hours}{minutes} o __{break_time_str}"
        more_lessons_today, next_period = get_next_period(break_start_datetime)[:2]
        bot.send_log("More lessons today:", more_lessons_today)
        if more_lessons_today:
            break_end_datetime = util.get_time(next_period, break_start_datetime, False)
            minutes = (break_end_datetime - break_start_datetime).seconds // 60
            break_time_str = util.get_formatted_period_time(next_period).split('-', maxsplit=1)[0]
            msg += f"—{break_time_str}__ ({minutes} min)."
        else:
            msg += "__ i jest to ostatnia przerwa."
    else:
        msg = f"{Emoji.INFO} Już jest po lekcjach!"
    return msg
