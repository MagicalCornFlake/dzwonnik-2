"""Module containing code relating to the 'plan' command."""

# Standard library imports
from datetime import datetime

# Third-party imports
from discord import Message, Embed
from corny_commons.util import web

# Local application imports
from modules import bot, util, Weekday, Emoji, WEEKDAY_NAMES
from modules.api import lesson_plan
from modules.commands import get_lessons_dp


DESC = """Pokazuje plan lekcji dla danego dnia, domyślnie dla naszej klasy na dzień dzisiejszy.
    Parametry: __dzień tygodnia__, __nazwa klasy__
    Przykłady:
    `{p}plan` - wyświetliłby się plan lekcji na dziś/najbliższy dzień szkolny.
    `{p}plan 2` - wyświetliłby się plan lekcji na wtorek (2. dzień tygodnia).
    `{p}plan pon` - wyświetliłby się plan lekcji na poniedziałek.
    `{p}plan pon 1a` - wyświetliłby się plan lekcji na poniedziałek dla klasy 1a."""


def get_weekday(day: int) -> str:
    """Returns a conjugated weekday name corresponding to the day number."""
    return WEEKDAY_NAMES[day].lower().replace("środa", "środę")


def get_lesson_description(period: int, day: int) -> str:
    """Gets the description for a given period in the lesson plan."""
    txt = f"Lekcja {period} ({util.get_formatted_period_time(period)})"
    is_current_lesson = (
        day == datetime.now().weekday() and period == util.current_period
    )
    lesson_description = f"*{txt}    <── TERAZ*" if is_current_lesson else txt
    return lesson_description


def format_lesson_plan(
    plan: dict[str, list[list[dict[str, any]]]], query_day: int, class_code: str
):
    """Formats the given lesson plan."""
    today_plan: list[list[dict[str, any]]] = plan[WEEKDAY_NAMES[query_day]]

    # The generator expression creates a list that maps each element from 'plan' to the boolean it
    # evaluates to. Empty lists are evaluated as False, non-empty lists are evaluated as True.
    # The sum function adds the contents of the list, keeping in mind that True = 1 and False = 0.
    # In essence, 'periods' evaluates to the number of non-empty lists in 'plan'.
    periods: int = sum([bool(lesson) for lesson in today_plan])
    first_period: int = 0

    desc = f"Liczba lekcji na **{get_weekday(query_day)}**: {periods}"
    try:
        lesson_plan_url = lesson_plan.get_plan_link(class_code)
    except ValueError:
        return f"{Emoji.WARNING} Nie powiodło się pobieranie planu lekcji dla klasy {class_code}."
    embed = Embed(
        title=f"Plan lekcji dla {class_code}", description=desc, url=lesson_plan_url
    )
    embed.set_footer(text=f"Użyj komendy {bot.prefix}plan, aby pokazać tą wiadomość.")

    for period in plan["Nr"]:
        if not today_plan[period]:
            # No lesson for the current period
            first_period += 1
            continue

        # Get all lessons this period
        lessons = today_plan[period]
        # Format each lesson object into a string
        lessons = [util.format_lesson_info(lesson, True) for lesson in lessons]
        lessons = "\n".join(lessons)

        embed.add_field(
            name=get_lesson_description(period, query_day), value=lessons, inline=False
        )
    return embed


def format_lesson_plan_dp(query_day: int) -> str or Embed:
    """Formats the lesson plan for DP."""
    embed = Embed(
        title=f"Plan lekcji dla {util.OUR_CLASS}",
        description=f"Wyświetlam plan na **{get_weekday(query_day)}**.",
    )
    embed.set_footer(text=f"Użyj komendy {bot.prefix}plan, aby pokazać tą wiadomość.")
    for period, _ in enumerate(util.lesson_plan_dp["times"]):
        lessons = "\n".join(get_lessons_dp(period, query_day))
        if not lessons:
            continue
        embed.add_field(
            name=get_lesson_description(period, query_day), value=lessons, inline=False
        )
    return embed


def get_lesson_plan(message: Message) -> str or Embed:
    """Event handler for the 'plan' command."""
    args: list[str] = message.content.split(" ")
    today = datetime.now().weekday()
    query_day = today if today < Weekday.SATURDAY else Weekday.MONDAY
    if len(args) > 1:
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
                    plan_id = lesson_plan.get_plan_id(args[2])
                except ValueError:
                    raise RuntimeError(f"invalid class name: {args[2]}") from None
                else:
                    class_code = args[2].lower()
                    try:
                        plan, _ = lesson_plan.get_lesson_plan(plan_id)
                    except web.WebException as web_exc:
                        # Invalid web response
                        return util.get_error_message(web_exc)
                    return format_lesson_plan(plan, query_day, class_code)
        except RuntimeError:
            return (
                f"{Emoji.WARNING} Należy napisać po komendzie `{bot.prefix}plan` numer "
                f"dnia (1-5) bądź dzień tygodnia, lub zostawić parametry komendy puste."
                f" Drugim opcjonalnym argumentem jest nazwa klasy."
            )

    return format_lesson_plan_dp(query_day)
