"""Module containing code relating to the 'nl' command."""

# Standard library imports
from datetime import datetime
from math import ceil

# Third-party imports
from discord import Message, Embed
from corny_commons.util import polish

# Local application imports
from . import LINK_404_URL, get_datetime_from_input, get_next_period, get_lesson_by_roles
from .. import bot, util, Emoji, Weekday, GROUP_NAMES


DESC = """Mówi jaką mamy następną lekcję.
    Parametry: __godzina__, __minuta__
    Przykład: `{p}nl 9 30` - wyświetliłaby się najbliższa lekcja po godzinie 09:30.
    *Domyślnie pokazana jest najbliższa lekcja od aktualnego czasu*"""


def get_next_lesson(message: Message) -> str or Embed:
    """Event handler for the 'nl' command."""
    time = get_datetime_from_input(message, 'nl')
    if not isinstance(time, datetime):
        return time

    def process(time: datetime) -> tuple[str, str]:
        # next_lesson_is_today, lesson_period, weekday_index = get_next_period(time)
        next_lesson = get_next_period(time)
        next_period = next_lesson[1]
        # If the period is 10 or more, subtract 9 from it.
        # The result of the boolean 'and' is the second expression (in this case 9).
        # If the condition is satisfied, the boolean expression returns 9, otherwise False (== 0).
        next_period -= next_lesson[1] > 9 and 9
        lesson = next_period, next_lesson[-1], message.author.roles
        lesson = get_lesson_by_roles(*lesson)
        if not lesson:
            return (f"{Emoji.INFO} Nie ma żadnych zajęć dla Twojej grupy"
                    f" po godzinie {time:%H:%M}.")
        bot.send_log("Received lesson:", lesson)
        if next_lesson[0]:
            if lesson['period'] > 10:
                # Currently lesson
                lesson_end_datetime = lesson['period'] - 10, time, True
                lesson_end_datetime = util.get_time(*lesson_end_datetime)
                bot.send_log("Lesson ending at:", lesson_end_datetime)
                # Get the next lesson after the end of this one, recursive call
                return process(lesson_end_datetime)
            # Currently break
            when = " "
            lesson_start_datetime = lesson['period'], time, False
            lesson_start_datetime = util.get_time(*lesson_start_datetime)
            bot.send_log("Lesson starting at:", lesson_start_datetime)
            mins = ceil((lesson_start_datetime - time).seconds / 60)
            hours = polish.conjugate_numeric(mins // 60, 'godzin')
            hours = (hours + " ") * (mins >= 60)
            countdown = f" (za {hours}{polish.conjugate_numeric(mins % 60, 'minut')})"
        else:
            when = Weekday.FRIDAY <= time.weekday() <= Weekday.SATURDAY
            when = " w poniedziałek" if when else " jutro"
            countdown = ""
        next_period_time = util.get_formatted_period_time(lesson["period"])
        next_period_time = next_period_time.split("-", maxsplit=1)[0]
        # Check if the group name has been mapped to a more user-friendly version
        temp_str: str = GROUP_NAMES.get(lesson['group'], lesson['group'])
        # Append a space if the group is not the entire class
        group = temp_str + " " * (lesson['group'] != "grupa_0")
        temp_str = util.get_lesson_name(lesson['name'])
        return (f"{Emoji.INFO} Następna lekcja {group}to **{temp_str}**{when} o godzinie "
                      f"__{next_period_time}__{countdown}."), util.get_lesson_link(lesson['name'])

    temp_var = process(time)
    try:
        msg, raw_link = temp_var
    except ValueError:
        # Return the error message if there's only one element in the result.
        return temp_var

    embed = Embed(title=f"Następna lekcja ({time:%H:%M})", description=msg)
    link = f"[meet.google.com](https://meet.google.com/{raw_link})" if raw_link else LINK_404_URL
    embed.add_field(name="Link do lekcji", value=link)
    temp_var = f"Użyj komendy {bot.prefix}nl, aby pokazać tą wiadomość."
    embed.set_footer(text=temp_var)
    return embed
