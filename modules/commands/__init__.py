"""__init__.py file for all modules responsible for functionality behind each user command."""

# Standard library imports
from datetime import datetime, timedelta

# Third-party imports
from discord import Role, Message, TextChannel

# Local application imports
from .. import Weekday, Emoji, WEEKDAY_NAMES, ROLE_CODES, util, bot


class HomeworkEvent:
    """Custom object type for homework events."""

    def __init__(self, title: str, group: int, author_id: int, deadline: str,
                 reminder_date_str: str = None, reminder_is_active: bool = True):
        self.event_id: int = None
        self.title: str = title
        self.group: int = group
        self.author_id: int = author_id
        self.deadline: str = deadline.split(' ')[0]
        if not reminder_date_str:
            deadline = datetime.strptime(deadline, "%d.%m.%Y %H")
            reminder_date = deadline - timedelta(days=1)
            reminder_date_str = datetime.strftime(reminder_date, "%d.%m.%Y %H")
        self.reminder_date = reminder_date_str
        self.reminder_is_active = reminder_is_active

    @property
    def serialised(self) -> dict[str, str or int or bool]:
        """Serialises the instance' attributes so that it can be saved in JSON format."""
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
    def id_string(self) -> str:
        """Returns a more human-readable version of the id with the 'event-id-' prefix."""
        return 'event-id-' + str(self.event_id)

    def sort_into_container(self, event_container: list) -> None:
        """Places the the event into homework_events in chronological order."""
        try:
            self.event_id = event_container[-1].id + 1
        except (IndexError, TypeError):
            self.event_id = 1
        for comparison_event in event_container:
            assert isinstance(comparison_event, HomeworkEvent)
            new_event_time = datetime.strptime(self.deadline, "%d.%m.%Y")
            comp_deadline: str = comparison_event.deadline
            old_event_time = datetime.strptime(comp_deadline, "%d.%m.%Y")
            # Dumps debugging data
            if new_event_time < old_event_time:
                # The new event should be placed before the one it is currently being compared to
                # Inserts event ID in the place of the one it's being compared to, so every event
                #   after this event (including the comparison one) is pushed ahead by one spot.
                event_container.insert(
                    event_container.index(comparison_event), self)
                return
            # The new event should not be placed before; continue evaluating.
        # Algorithm was unable to place the event before any others, so it shall be put at the end.
        event_container.append(self)


class HomeworkEventContainer(list[HomeworkEvent]):
    """Custom object class that derives from the list base type.
    This object serves as a container for HomeworkEvent objects.
    Defines methods for JSON serialisation as well as contents optimisation.
    """

    @property
    def serialised(self) -> list[dict[str, str or int or bool]]:
        """Serialises each event in the container."""
        return [event.serialised for event in self]

    def remove_disjunction(self, reference_container: list) -> None:
        """Removes events from this container that are not present in the reference container."""
        assert isinstance(reference_container, HomeworkEventContainer)
        for event in self:
            if event.serialised not in reference_container.serialised:
                rm_obsolete_event_msg = f"Removing obsolete event '{event.title}' from container"
                bot.send_log(rm_obsolete_event_msg)
                self.remove(event)


class TrackedItem:
    """Custom object type that contains information about a tracked item on the Steam Market."""

    def __init__(self, name: str, min_price: int, max_price: int, author_id: int) -> None:
        self.name: str = name
        self.min_price: int = min_price
        self.max_price: int = max_price
        self.author_id: int = author_id

    @property
    def serialised(self) -> dict[str, int or str]:
        """Serialises the instance's attributes so that it can be saved in JSON format."""
        return {
            "name": self.name,
            "min_price": self.min_price,
            "max_price": self.max_price,
            "author_id": self.author_id
        }

    def __eq__(self, other) -> bool:
        if isinstance(other, type(self)):
            # return self.name.lower() == other.name.lower()
            return self.serialised == other.serialised
        return False


homework_events = HomeworkEventContainer()
tracked_market_items: list[TrackedItem] = []


def ensure_sender_is_admin(message: Message, error_message: str = None) -> None:
    """Raises an exception if the message author is not an administrator."""
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

    Returns a tuple consisting of a boolean indicating if that day is today, the period number,
    and the day of the week.
    If the current time is during a lesson, the period number will be incremented by 10.
    """
    bot.send_log(f"Getting next period for {given_time:%d/%m/%Y %X} ...")
    current_day_index: int = given_time.weekday()

    if current_day_index < Weekday.SATURDAY:
        for period, times in enumerate(util.lesson_plan["Godz"]):
            for is_during_lesson, time in enumerate(times):
                hour, minute = time
                if given_time.hour * 60 + given_time.minute < hour * 60 + minute:
                    when = "lesson" if is_during_lesson else "break"
                    found = f"... this is before {hour:02}:{minute:02} (period {period} {when})."
                    bot.send_log(found)
                    return True, period + 10 * is_during_lesson, current_day_index
        # Could not find any such lesson.
        # If it's currently Friday, the modulo operation will return 0 (Monday).
        next_school_day: Weekday = (current_day_index + 1) % Weekday.SATURDAY
    else:
        next_school_day = Weekday.MONDAY

    # If it's currently weekend or after the last lesson for the day
    bot.send_log(
        f"... there are no more lessons today. Next school day: {next_school_day}")
    first_period = -1  # Initialise so PyLint doesn't complain
    for first_period, lessons in enumerate(util.lesson_plan[WEEKDAY_NAMES[next_school_day]]):
        # Stop incrementing 'first_period' when the 'lessons' object is a non-empty list
        if lessons:
            break
    return False, first_period, next_school_day


def get_lesson_by_roles(query_period: int, weekday: int, roles: list[str, Role]) -> dict[str, str]:
    """Get the lesson details for a given period, day and user roles list.
    Arguments:
        query_period -- the period number to look for.
        weekday -- the index of the weekday to look at.
        roles -- the roles of the user that the lesson is defined to be intended for.

    Returns a dictionary containing the lesson details including the period, or an empty dictionary
    if no lesson was found.
    """
    target_roles = ["grupa_0"]
    for role in roles:
        if role in ROLE_CODES or str(role) in ROLE_CODES.values():
            target_roles.append(str(role))
    weekday_name = WEEKDAY_NAMES[weekday]
    looking_msg = f"{query_period} on {weekday_name} with roles: {target_roles})"
    bot.send_log("Looking for lesson of period " + looking_msg)
    for period, lessons in enumerate(util.lesson_plan[weekday_name]):
        if period < query_period:
            continue
        for lesson in lessons:
            if lesson["group"] in target_roles or ROLE_CODES[lesson["group"]] in target_roles:
                found_lesson_msg = (f"Found lesson '{lesson['name']}' for '{lesson['group']}'"
                                    f" on period {period}.")
                bot.send_log(found_lesson_msg)
                lesson["period"] = period
                return lesson
    bot.send_log(
        f"Did not find a lesson matching those roles for period {query_period} on {weekday_name}.")
    return {}


def get_datetime_from_input(message: Message, calling_command: str) -> datetime or str:
    """Parses the message content and returns a datetime object if it contains a valid time.
    
    Returns the current date and time if there are no valid time parameters in the message content.
    """
    args: list[str] = message.content.split(" ")
    current_time = datetime.now()
    if len(args) == 1:
        # No input parameters; return the current time as-is
        return True, current_time
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
            # Minute not specified by user; use default of :00.
            args.append("00")
        except ValueError:
            # NaN
            error_description = f"`{':'.join(args[1:])}` nie jest godziną."
            raise RuntimeError(error_description) from None
    except RuntimeError as invalid_arg_exc:
        msg = f"{Emoji.WARNING} {invalid_arg_exc}\nNależy napisać po komendzie " + \
            f"`{bot.prefix}{calling_command}` godzinę i ewentualnie minutę oddzieloną spacją"
        return False, msg + ", lub zostawić parametry komendy puste."
    params = {
        "hour": int(args[1]),
        "minute": int(args[2]),
        "second": 0,
        "microsecond": 0
    }
    return True, current_time.replace(**params)
