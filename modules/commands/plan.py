"""Module containing code relating to the 'plan' command."""

# Standard library imports
from datetime import datetime

# Third-party imports
from discord import Message, Embed

# Local application imports
from .. import Weekday, weekday_names, Emoji, prefix, group_names, current_period, util
# from ..util import util.send_log, get_lesson_link, get_lesson_name, get_formatted_period_time
from ..util.crawlers import plan_crawler

def get_lesson_plan(message: Message) -> tuple[bool, str or Embed]:
    args = message.content.split(" ")
    today = datetime.now().weekday()
    class_lesson_plan = util.lesson_plan
    if len(args) == 1:
        query_day = today if today < Weekday.saturday else Weekday.monday
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
                        raise RuntimeError(f"{args[1]} is not a number between 1 and 5.")
                    else:
                        # It is, and of correct format
                        query_day = int(args[1]) - 1
                except ValueError:
                    # The input is not a number.
                    # Check if it is a day of the week
                    for i, weekday in enumerate(weekday_names):
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
                    plan_id = plan_crawler.get_plan_id(args[2])
                except ValueError:
                    raise RuntimeError(f"invalid class name: {args[2]}")
                else:
                    class_lesson_plan = plan_crawler.get_util.lesson_plan(plan_id)[0]
        except RuntimeError as e:
            util.send_log(f"Handling exception with args: '{' '.join(args[1:])}' ({type(e).__name__}: \"{e}\")")
            return False, f"{Emoji.warning} Należy napisać po komendzie `{prefix}plan` numer dnia (1-5) " \
                          f"bądź dzień tygodnia, lub zostawić parametry komendy puste. Drugim opcjonalnym argumentem jest nazwa klasy."

    plan = class_lesson_plan[weekday_names[query_day]]

    # The generator expression creates a list that maps each element from 'plan' to the boolean it evaluates to.
    # Empty lists are evaluated as False, non-empty lists are evaluated as True.
    # The sum() function adds the contents of the list, keeping in mind that True == 1 and False == 0.
    # In essence, 'periods' evaluates to the number of non-empty lists in 'plan' (i.e. the number of lessons on that day).
    periods: int = sum([bool(lesson) for lesson in plan])
    first_period: int = 0

    desc = f"Plan lekcji na **{weekday_names[query_day].lower().replace('środa', 'środę')}** ({periods} lekcji) jest następujący:"
    embed = Embed(title="Plan lekcji", description=desc)
    embed.set_footer(text=f"Użyj komendy {prefix}plan, aby pokazać tą wiadomość.")

    for period in class_lesson_plan["Nr"]:
        if not plan[period]:
            # No lesson for the current period
            first_period += 1
            continue
        lesson_texts = []
        for lesson in plan[period]:
            raw_link = util.get_lesson_link(lesson['name'])
            link = f"https://meet.google.com/{raw_link}?authuser=0" if raw_link else "http://guzek.uk/error/404?lang=pl-PL&source=discord"
            lesson_texts.append(f"[{util.get_lesson_name(lesson['name'])} - sala {lesson['room_id']}]({link})")
            if lesson['group'] != "grupa_0":
                lesson_texts[-1] += f" ({group_names[lesson['group']]})"
        txt = f"Lekcja {period} ({util.get_formatted_period_time(period)})"
        is_current_lesson = query_day == today and period == current_period 
        embed.add_field(name=f"*{txt}    <── TERAZ*" if is_current_lesson else txt, value='\n'.join(lesson_texts), inline=False)
    return True, embed
