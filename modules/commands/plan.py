"""Module containing code relating to the 'plan' command."""

# Standard library imports
from datetime import datetime

# Third-party imports
from discord import Message, Embed

# Local application imports
from .. import Weekday, WEEKDAY_NAMES, Emoji, GROUP_NAMES, util, bot
from ..util import web
from ..util.crawlers import lesson_plan as lesson_plan_crawler


DESC = """Pokazuje plan lekcji dla danego dnia, domyślnie naszej klasy oraz na dzień dzisiejszy.
    Parametry: __dzień tygodnia__, __nazwa klasy__
    Przykłady:
    `{p}plan` - wyświetliłby się plan lekcji na dziś/najbliższy dzień szkolny.
    `{p}plan 2` - wyświetliłby się plan lekcji na wtorek (2. dzień tygodnia).
    `{p}plan pon` - wyświetliłby się plan lekcji na poniedziałek.
    `{p}plan pon 1a` - wyświetliłby się plan lekcji na poniedziałek dla klasy 1a."""


def get_lesson_plan(message: Message) -> tuple[bool, str or Embed]:
    args = message.content.split(" ")
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
                        raise RuntimeError(err_msg)
                    else:
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
                    # 'query_day' will have the default value of -1 if the above for loop didn't find any matches
                    if query_day == -1:
                        # The input is not a valid weekday name.
                        # ValueError can't be used since it has already been caught
                        raise RuntimeError(f"invalid weekday name: {args[1]}")
            if len(args) > 2:
                try:
                    plan_id = lesson_plan_crawler.get_plan_id(args[2])
                except ValueError:
                    raise RuntimeError(f"invalid class name: {args[2]}")
                else:
                    class_code = args[2]
                    try:
                        result = lesson_plan_crawler.get_lesson_plan(plan_id)
                    except Exception as e:
                        # Invalid web response; if the exception is something else, it is raised again
                        return False, web.get_error_message(e)
                    else:
                        class_lesson_plan = result[0]
        except RuntimeError as e:
            handling_exception = f"Handling exception with args: '{' '.join(args[1:])}' ({type(e).__name__}: \"{e}\")"
            bot.send_log(handling_exception, force=True)
            return False, f"{Emoji.WARNING} Należy napisać po komendzie `{bot.prefix}plan` numer dnia (1-5) " \
                          f"bądź dzień tygodnia, lub zostawić parametry komendy puste. Drugim opcjonalnym argumentem jest nazwa klasy."

    plan = class_lesson_plan[WEEKDAY_NAMES[query_day]]

    # The generator expression creates a list that maps each element from 'plan' to the boolean it evaluates to.
    # Empty lists are evaluated as False, non-empty lists are evaluated as True.
    # The sum() function adds the contents of the list, keeping in mind that True == 1 and False == 0.
    # In essence, 'periods' evaluates to the number of non-empty lists in 'plan' (i.e. the number of lessons on that day).
    periods: int = sum([bool(lesson) for lesson in plan])
    first_period: int = 0

    title = f"Plan lekcji {class_code}"
    desc = f"Plan lekcji na **{WEEKDAY_NAMES[query_day].lower().replace('środa', 'środę')}** ({periods} lekcji) jest następujący"
    lesson_plan_url = lesson_plan_crawler.get_plan_link(class_code)
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
            link = f"https://meet.google.com/{raw_link}" if raw_link else "http://guzek.uk/error/404?lang=pl-PL&source=discord"
            lesson_name = util.get_lesson_name(lesson['name'])
            room = lesson['room_id']
            lesson_texts.append(f"[{lesson_name} - sala {room}]({link})")
            if lesson['group'] != "grupa_0":
                group_name = GROUP_NAMES.get(lesson['group'], lesson['group'])
                lesson_texts[-1] += f" ({group_name})"
        txt = f"Lekcja {period} ({util.get_formatted_period_time(period)})"
        is_current_lesson = query_day == today and period == bot.current_period
        lesson_description = f"*{txt}    <── TERAZ*" if is_current_lesson else txt
        lessons = '\n'.join(lesson_texts)
        embed.add_field(name=lesson_description, value=lessons, inline=False)
    return True, embed
