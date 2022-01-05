"""Module containing code relating to the 'nl' command."""

# Standard library imports
from datetime import datetime
from math import ceil

# Third-party imports
from discord import Message, Embed

# Local application imports
from . import get_datetime_from_input, get_next_period, get_lesson_by_roles
from .. import bot, util, Emoji, Weekday, group_names


desc = """Mówi jaką mamy następną lekcję.
    Parametry: __godzina__, __minuta__
    Przykład: `{p}nl 9 30` - wyświetliłaby się najbliższa lekcja po godzinie 09:30.
    *Domyślnie pokazana jest najbliższa lekcja od aktualnego czasu*"""


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
        bot.send_log("Received lesson:", lesson)
        if next_lesson_is_today:
            if lesson['period'] > 10:
                # Currently lesson
                lesson_end_datetime = util.get_time(lesson['period'] - 10, current_time, True)
                bot.send_log("Lesson ending at:", lesson_end_datetime)
                # Get the next lesson after the end of this one, recursive call
                return process(lesson_end_datetime)
            # Currently break
            when = " "
            lesson_start_datetime = util.get_time(lesson['period'], current_time, False)
            bot.send_log("Lesson starting at:", lesson_start_datetime)
            mins = ceil((lesson_start_datetime - current_time).seconds / 60)
            countdown = f" (za {(util.conjugate_numeric(mins // 60, 'godzin') + ' ') * (mins >= 60)}{util.conjugate_numeric(mins % 60, 'minut')})"
        else:
            when = " w poniedziałek" if Weekday.friday <= current_time.weekday() <= Weekday.saturday else " jutro"
            countdown = ""
        next_period_time = util.get_formatted_period_time(lesson["period"]).split("-")[0]
        # Check if the group name has been mapped to a more user-friendly version; otherwise use the group code
        group_name: str = group_names.get(lesson['group'], lesson['group'])
        # Append a space if the group is not the entire class
        group = group_name + " " * (lesson['group'] != "grupa_0")
        return True, f"{Emoji.info} Następna lekcja {group}to **{util.get_lesson_name(lesson['name'])}**" \
                     f"{when} o godzinie __{next_period_time}__{countdown}.", util.get_lesson_link(lesson['name'])

    success, msg, raw_link = process(current_time)
    if not success:
        return False, msg

    embed = Embed(title=f"Następna lekcja ({current_time:%H:%M})", description=msg)
    link = f"[meet.google.com](https://meet.google.com/{raw_link})" if raw_link else "[brak](http://guzek.uk/error/404?lang=pl-PL&source=discord)"
    embed.add_field(name="Link do lekcji", value=link)
    embed.set_footer(text=f"Użyj komendy {bot.prefix}nl, aby pokazać tą wiadomość.")
    return True, embed
