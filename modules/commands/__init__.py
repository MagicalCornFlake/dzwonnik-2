"""__init__.py file for all modules responsible for functionality behind each user command."""

# Standard library imports
from datetime import datetime
from typing import Text

# Third-party imports
from discord import Role, Message, TextChannel

# Local application imports
from .. import Weekday, Emoji, WEEKDAY_NAMES, ROLE_CODES, util, bot


class HomeworkEvent:
    def __init__(self, title, group, author_id, deadline, reminder_date=None, reminder_is_active=True):
        self.id = None
        self.title = title
        self.group = group
        self.author_id = author_id
        self.deadline = deadline.split(' ')[0]
        if reminder_date is None:
            reminder_date = datetime.datetime.strftime(datetime.datetime.strptime(
                deadline, "%d.%m.%Y %H") - datetime.timedelta(days=1), "%d.%m.%Y %H")
        self.reminder_date = reminder_date
        self.reminder_is_active = reminder_is_active

    @property
    def serialised(self):
        # Returns a dictionary with all the necessary data for a given instance to be able to save it in a .json file
        event_details = {
            'title': self.title,
            'group': self.group,
            'author_id': self.author_id,
            'deadline': self.deadline,
            'reminder_date': self.reminder_date,
            'reminder_is_active': self.reminder_is_active,
        }
        return event_details

    @property
    def id_string(self):
        # Returns a more human-readable version of the id with the 'event-id-' suffix
        return 'event-id-' + str(self.id)

    def sort_into_container(self, event_container):
        # Places the the event in chronological order into homework_events
        try:
            self.id = event_container[-1].id + 1
        except (IndexError, TypeError):
            self.id = 1
        for comparison_event in event_container:
            new_event_time = datetime.datetime.strptime(
                self.deadline, "%d.%m.%Y")
            old_event_time = datetime.datetime.strptime(
                comparison_event.deadline, "%d.%m.%Y")
            # Dumps debugging data
            if new_event_time < old_event_time:
                # The new event should be placed chronologically before the one it is currently being compared to
                # Inserts event id in the place of the one it's being compared to, so every event
                # after this event (including the comparison one) is pushed one spot ahead in the list
                event_container.insert(
                    event_container.index(comparison_event), self)
                return
            # The new event should not be placed before the one it is currently being compared to, continue evaluating
        # At this point the algorithm was unable to place the event before any others, so it shall be put at the end
        event_container.append(self)


class HomeworkEventContainer(list[HomeworkEvent]):
    @property
    def serialised(self):
        return [event.serialised for event in self]

    def remove_disjunction(self, reference_container):
        for event in self:
            if event.serialised not in reference_container.serialised:
                bot.send_log(
                    f"Removing obsolete event '{event.title}' from container")
                self.remove(event)


class TrackedItem:
    def __init__(self, name, min_price, max_price, author_id):
        self.name = name
        self.min_price = min_price
        self.max_price = max_price
        self.author_id = author_id

    @property
    def serialised(self):
        return {
            "name": self.name,
            "min_price": self.min_price,
            "max_price": self.max_price,
            "author_id": self.author_id
        }

    def __eq__(self, other):
        if type(other) is type(self):
            return self.name.lower() == other.name.lower()
        return False


homework_events = HomeworkEventContainer()
tracked_market_items: list[TrackedItem] = []


def ensure_sender_is_admin(message: Message, error_message: str = None) -> None:
    """Raises the `modules.bot.MissingPermissionsException` if the message author is not an administrator."""
    message_content: str = message.content
    msg_first_word = message_content.split(' ', maxsplit=1)[0]
    default_msg = f"korzystania z komendy `{bot.prefix}{msg_first_word}`"
    chnl: TextChannel = message.channel
    if not chnl.permissions_for(message.author).administrator:
        raise bot.MissingPermissionsException(error_message or default_msg)


def get_next_period(given_time: datetime) -> tuple[bool, int, int]:
    """Get the information about the next period for a given time.

    Arguments:
        given_time -- the start time to base the search off of.

    Returns a tuple consisting of a boolean indicating if that day is today, the period number, and the day of the week.
    If the current time is during a lesson, the period number will be incremented by 10.
    """
    bot.send_log(f"Getting next period for {given_time:%d/%m/%Y %X} ...")
    current_day_index: int = given_time.weekday()

    if current_day_index < Weekday.SATURDAY:
        for period, times in enumerate(util.lesson_plan["Godz"]):
            for is_during_lesson, time in enumerate(times):
                hour, minute = time
                if given_time.hour * 60 + given_time.minute < hour * 60 + minute:
                    bot.send_log(
                        f"... this is before {hour:02}:{minute:02} (period {period} {'lesson' if is_during_lesson else 'break'}).")
                    return True, period + 10 * is_during_lesson, current_day_index
        # Could not find any such lesson.
        # current_day_index == Weekday.friday == 4  -->  next_school_day == (current_day_index + 1) % Weekday.saturday == (4 + 1) % 5 == 0 == Weekday.monday
        next_school_day = (current_day_index + 1) % Weekday.SATURDAY
    else:
        next_school_day = Weekday.MONDAY

    # If it's currently weekend or after the last lesson for the day
    bot.send_log(
        f"... there are no more lessons today. Next school day: {next_school_day}")
    for first_period, lessons in enumerate(util.lesson_plan[WEEKDAY_NAMES[next_school_day]]):
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
    target_roles = [
        "grupa_0"] + [str(role) for role in roles if role in ROLE_CODES or str(role) in ROLE_CODES.values()]
    weekday_name = WEEKDAY_NAMES[weekday_index]
    bot.send_log(
        f"Looking for lesson of period {query_period} on {weekday_name} with roles: {target_roles})")
    for period, lessons in enumerate(util.lesson_plan[weekday_name]):
        if period < query_period:
            continue
        for lesson in lessons:
            if lesson["group"] in target_roles or ROLE_CODES[lesson["group"]] in target_roles:
                bot.send_log(
                    f"Found lesson '{lesson['name']}' for group '{lesson['group']}' on period {period}.")
                lesson["period"] = period
                return lesson
    bot.send_log(
        f"Did not find a lesson matching those roles for period {query_period} on {weekday_name}.")
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
                        raise RuntimeError(
                            f"Godzina ('{args[2]}') nie znajduje się w przedziale `0, 59`.")
                else:
                    raise RuntimeError(
                        f"Minuta ('{args[1]}') nie znajduje się w przedziale `0, 23`.")
            except IndexError:
                # Minute not specified by user
                args.append(00)
            except ValueError:
                # NaN
                raise RuntimeError(f"`{':'.join(args[1:])}` nie jest godziną.")
        except RuntimeError as e:
            msg = f"{Emoji.WARNING} {e}\nNależy napisać po komendzie `{bot.prefix}{calling_command}` godzinę" \
                  f" i ewentualnie minutę oddzieloną spacją, lub zostawić parametry komendy puste. "
            return False, msg
        current_time = current_time.replace(
            hour=int(args[1]), minute=int(args[2]), second=0, microsecond=0)
    return True, current_time
