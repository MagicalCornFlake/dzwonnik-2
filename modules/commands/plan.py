"""Module containing code relating to the 'plan' command."""

# Standard library imports
from datetime import datetime

# Third-party imports
from discord import Message, Embed
from corny_commons.util import web

# Local application imports
from . import LINK_404_URL
from .. import util, bot, Weekday, Emoji, WEEKDAY_NAMES, GROUP_NAMES
from ..util.crawlers import lesson_plan as lesson_plan_api


DESC = """Pokazuje plan lekcji dla danego dnia, domyślnie naszej klasy oraz na dzień dzisiejszy.
    Parametry: __dzień tygodnia__, __nazwa klasy__
    Przykłady:
    `{p}plan` - wyświetliłby się plan lekcji na dziś/najbliższy dzień szkolny.
    `{p}plan 2` - wyświetliłby się plan lekcji na wtorek (2. dzień tygodnia).
    `{p}plan pon` - wyświetliłby się plan lekcji na poniedziałek.
    `{p}plan pon 1a` - wyświetliłby się plan lekcji na poniedziałek dla klasy 1a."""


def get_lesson_plan(message: Message) -> str or Embed:
    """Event handler for the 'plan' command."""
    args: list[str] = message.content.split(" ")
    today = datetime.now().weekday()
    class_lesson_plan = util.lesson_plan
    class_code = util.OUR_CLASS
    if len(args) == 1:
        query_day = today if today < Weekday.SATURDAY else Weekday.MONDAY
    else:
        query_day = -1
        # This 'try' clause raises RuntimeError if the input is invalid for whatever reason
        try:
            try:
                query_day = {"pn": 0, "śr": 2, "sr": 2, "pt": 4}[args[1]]
            except KeyError:
                try:
                    # Check if the input is a number
                    if not 1 <= int(args[1]) <= 5:
                        # It is, but of invalid format
                        err_msg = f"{args[1]} is not a number between 1 and 5."
                        raise RuntimeError(err_msg) from None
                    # It is, and of correct format
                    query_day = int(args[1]) - 1
                except ValueError:
                    # The input is not a number.
                    # Check if it is a day of the week
                    for i, weekday in enumerate(WEEKDAY_NAMES):
                        if weekday.lower().startswith(args[1].lower()):
                            # The input is a valid weekday name.
                            query_day = i
                            break
                    # 'query_day' == -1 if there are no matched lessons from the above loop.
                    if query_day == -1:
                        # The input is not a valid weekday name.
                        # ValueError can't be used since it has already been caught
                        err_msg = f"invalid weekday name: {args[1]}"
                        raise RuntimeError(err_msg) from None
            if len(args) > 2:
                try:
                    plan_id = lesson_plan_api.get_plan_id(args[2])
                except ValueError:
                    raise RuntimeError(f"invalid class name: {args[2]}") from None
                else:
                    class_code = args[2]
                    try:
                        result = lesson_plan_api.get_lesson_plan(plan_id)
                    except web.WebException as web_exc:
                        # Invalid web response
                        return util.get_error_message(web_exc)
                    else:
                        class_lesson_plan = result[0]
        except RuntimeError:
            return (f"{Emoji.WARNING} Należy napisać po komendzie `{bot.prefix}plan` numer "
                           f"dnia (1-5) bądź dzień tygodnia, lub zostawić parametry komendy puste."
                           f" Drugim opcjonalnym argumentem jest nazwa klasy.")

    plan: list[list[dict[str, any]]] = class_lesson_plan[WEEKDAY_NAMES[query_day]]

    # The generator expression creates a list that maps each element from 'plan' to the boolean it
    # evaluates to. Empty lists are evaluated as False, non-empty lists are evaluated as True.
    # The sum function adds the contents of the list, keeping in mind that True = 1 and False = 0.
    # In essence, 'periods' evaluates to the number of non-empty lists in 'plan'.
    periods: int = sum([bool(lesson) for lesson in plan])  #  number of lessons on the given day
    first_period: int = 0

    title = f"Plan lekcji {class_code}"
    weekday = WEEKDAY_NAMES[query_day].lower().replace('środa', 'środę')
    desc = f"Liczba lekcji na **{weekday}**: {periods}"
    lesson_plan_url = lesson_plan_api.get_plan_link(class_code)
    embed = Embed(title=title, description=desc, url=lesson_plan_url)
    footer = f"Użyj komendy {bot.prefix}plan, aby pokazać tą wiadomość."
    embed.set_footer(text=footer)

    for period in class_lesson_plan["Nr"]:
        if not plan[period]:
            # No lesson for the current period
            first_period += 1
            continue
        lesson_texts = []
        for lesson in plan[period]:
            raw_link = util.get_lesson_link(lesson['name'])
            link = f"https://meet.google.com/{raw_link}" if raw_link else LINK_404_URL
            lesson_name = util.get_lesson_name(lesson['name'])
            room = lesson['room_id']
            lesson_texts.append(f"[{lesson_name} - sala {room}]({link})")
            if lesson['group'] != "grupa_0":
                group_name = GROUP_NAMES.get(lesson['group'], lesson['group'])
                lesson_texts[-1] += f" ({group_name})"
        txt = f"Lekcja {period} ({util.get_formatted_period_time(period)})"
        is_current_lesson = query_day == today and period == util.current_period
        lesson_description = f"*{txt}    <── TERAZ*" if is_current_lesson else txt
        lessons = '\n'.join(lesson_texts)
        embed.add_field(name=lesson_description, value=lessons, inline=False)
    return embed
