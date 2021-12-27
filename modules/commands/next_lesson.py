"""Module containing code relating to the 'nl' command."""

# Standard library imports
from datetime import datetime
from math import ceil

# Third-party imports
from discord import Message, Embed

# Local application imports
from .import get_datetime_from_input, get_next_period, get_lesson_by_roles
from ..import prefix, Emoji, group_names, Weekday
from ..file_manager import send_log
from ..util import get_time, conjugate_numeric, get_formatted_period_time, get_lesson_link, get_lesson_name

# Returns the message to send when the user asks for the next lesson
def get_next_lesson(message: Message) -> tuple[bool, str or Embed]:
    success, result = get_datetime_from_input(message, 'nl')
    if not success:
        return False, result
    current_time: datetime = result

    def process(time: datetime) -> tuple[bool, str, str]:
        next_lesson_is_today, lesson_period, weekday_index = get_next_period(time)
        lesson = get_lesson_by_roles(lesson_period if lesson_period < 10 else lesson_period - 9, weekday_index, message.author.roles)
        if not lesson:
            return False, f"{Emoji.info} Nie ma żadnych zajęć dla Twojej grupy po godz. {time:%H:%M}.", ""
        send_log("Received lesson:", lesson)
        if next_lesson_is_today:
            if lesson['period'] > 10:
                # Currently lesson
                lesson_end_datetime = get_time(lesson['period'] - 10, current_time, True)
                send_log("Lesson ending at:", lesson_end_datetime)
                # Get the next lesson after the end of this one, recursive call
                return process(lesson_end_datetime)
            # Currently break
            when = " "
            lesson_start_datetime = get_time(lesson['period'], current_time, False)
            send_log("Lesson starting at:", lesson_start_datetime)
            mins = ceil((lesson_start_datetime - current_time).seconds / 60)
            countdown = f" (za {(conjugate_numeric(mins // 60, 'godzin') + ' ') * (mins >= 60)}{conjugate_numeric(mins % 60, 'minut')})"
        else:
            when = " w poniedziałek" if Weekday.friday <= current_time.weekday() <= Weekday.saturday else " jutro"
            countdown = ""
        next_period_time = get_formatted_period_time(lesson["period"]).split("-")[0]
        group = group_names[lesson['group']] + " " * (lesson['group'] != "grupa_0")
        return True, f"{Emoji.info} Następna lekcja {group}to **{get_lesson_name(lesson['name'])}**" \
                     f"{when} o godzinie __{next_period_time}__{countdown}.", get_lesson_link(lesson['name'])

    success, msg, raw_link = process(current_time)
    if not success:
        return False, msg

    embed = Embed(title=f"Następna lekcja ({current_time:%H:%M})", description=msg)
    link = f"[meet.google.com](https://meet.google.com/{raw_link}?authuser=0)" if raw_link else "[brak](http://guzek.uk/error/404?lang=pl-PL&source=discord)"
    embed.add_field(name="Link do lekcji", value=link)
    embed.set_footer(text=f"Użyj komendy {prefix}nl, aby pokazać tą wiadomość.")
    return True, embed
