"""__init__.py file for all modules responsible for functionality behind each user command."""

# Standard library imports
from datetime import datetime

# Third-party imports
from discord import Role, Message

# Local application imports
from .. import Weekday, Emoji, weekday_names, role_codes, prefix
from .. util import send_log, lesson_plan


def get_next_period(given_time: datetime) -> tuple[bool, int, int]:
    """Get the information about the next period for a given time.

    Arguments:
        given_time -- the start time to base the search off of.

    Returns a tuple consisting of a boolean indicating if that day is today, the period number, and the day of the week.
    If the current time is during a lesson, the period number will be incremented by 10.
    """
    send_log(f"Getting next period for {given_time:%d/%m/%Y %X} ...")
    current_day_index: int = given_time.weekday()

    if current_day_index < Weekday.saturday:
        for period, times in enumerate(lesson_plan["Godz"]):
            for is_during_lesson, time in enumerate(times):
                hour, minute = time
                if given_time.hour * 60 + given_time.minute < hour * 60 + minute:
                    send_log(f"... this is before {hour:02}:{minute:02} (period {period} {'lesson' if is_during_lesson else 'break'}).")
                    return True, period + 10 * is_during_lesson, current_day_index
        # Could not find any such lesson.
        # current_day_index == Weekday.friday == 4  -->  next_school_day == (current_day_index + 1) % Weekday.saturday == (4 + 1) % 5 == 0 == Weekday.monday
        next_school_day = (current_day_index + 1) % Weekday.saturday
    else:
        next_school_day = Weekday.monday

    # If it's currently weekend or after the last lesson for the day
    send_log(f"... there are no more lessons today. Next school day: {next_school_day}")
    for first_period, lessons in enumerate(lesson_plan[weekday_names[next_school_day]]):
        # Stop incrementing 'first_period' when the 'lessons' object is a non-empty list
        if lessons:
            break
    return False, first_period, next_school_day


def get_lesson_by_roles(query_period: int, weekday_index: int, roles: list[str, Role]) -> dict[str, str]:
    """Get the lesson details for a given period, day and user roles list.
    Arguments:
        query_period -- the period number to look for.
        weekday_index -- the index of the weekday to look at.
        roles -- the roles of the user that the lesson is defined to be intended for.

    Returns a dictionary containing the lesson details including the period, or an empty dictionary if no lesson was found.
    """
    target_roles = ["grupa_0"] + [str(role) for role in roles if role in role_codes or str(role) in role_codes.values()]
    weekday_name = weekday_names[weekday_index]
    send_log(f"Looking for lesson of period {query_period} on {weekday_name} with roles: {target_roles})")
    for period, lessons in enumerate(lesson_plan[weekday_name]):
        if period < query_period:
            continue
        for lesson in lessons:
            if lesson["group"] in target_roles or role_codes[lesson["group"]] in target_roles:
                send_log(f"Found lesson '{lesson['name']}' for group '{lesson['group']}' on period {period}.")
                lesson["period"] = period
                return lesson
    send_log(f"Did not find a lesson matching those roles for period {query_period} on {weekday_name}.", force=True)
    return {}


def get_datetime_from_input(message: Message, calling_command: str) -> tuple[bool, str or datetime]:
    args = message.content.split(" ")
    current_time = datetime.now()
    if len(args) > 1:
        try:
            # Input validation
            try:
                if 0 <= int(args[1]) < 24:
                    if not 0 <= int(args[2]) < 60:
                        raise RuntimeError(f"Godzina ('{args[2]}') nie znajduje się w przedziale `0, 59`.")
                else:
                    raise RuntimeError(f"Minuta ('{args[1]}') nie znajduje się w przedziale `0, 23`.")
            except IndexError:
                # Minute not specified by user
                args.append(00)
            except ValueError:
                # NaN
                raise RuntimeError(f"`{':'.join(args[1:])}` nie jest godziną.")
        except RuntimeError as e:
            msg = f"{Emoji.warning} {e}\nNależy napisać po komendzie `{prefix}{calling_command}` godzinę" \
                  f" i ewentualnie minutę oddzieloną spacją, lub zostawić parametry komendy puste. "
            return False, msg
        current_time = current_time.replace(hour=int(args[1]), minute=int(args[2]), second=0, microsecond=0)
    return True, current_time