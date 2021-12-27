"""Module containing code relating to the 'zad' command."""

# Standard library imports
import datetime

# Third-party imports
from discord import Message, Embed

# Local application imports
from .. import prefix, Emoji, role_codes, group_names
from .. file_manager import read_data_file, save_data_file
from .. util import send_log

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
            new_event_time = datetime.datetime.strptime(self.deadline, "%d.%m.%Y")
            old_event_time = datetime.datetime.strptime(comparison_event.deadline, "%d.%m.%Y")
            # Dumps debugging data
            if new_event_time < old_event_time:
                # The new event should be placed chronologically before the one it is currently being compared to
                # Inserts event id in the place of the one it's being compared to, so every event
                # after this event (including the comparison one) is pushed one spot ahead in the list
                event_container.insert(event_container.index(comparison_event), self)
                return
            # The new event should not be placed before the one it is currently being compared to, continue evaluating
        # At this point the algorithm was unable to place the event before any others, so it shall be put at the end
        event_container.append(self)


class HomeworkEventContainer(list):
    @property
    def serialised(self):
        return [event.serialised for event in self]

    def remove_disjunction(self, reference_container):
        for event in self:
            if event.serialised not in reference_container.serialised:
                send_log(f"Removing obsolete event '{event.title}' from container")
                self.remove(event)


homework_events = HomeworkEventContainer()


def process_homework_events_alias(message: Message) -> tuple[bool, str or Embed]:
    args = message.content.split(" ")
    if len(args) == 1:
        return get_homework_events(message)
    elif len(args) < 4:
        return False, f"{Emoji.warning} Należy napisać po komendzie `{prefix}zad` termin oddania zadania, oznaczenie " + \
            "grupy, dla której jest zadanie oraz jego treść, lub 'del' i ID zadania, którego się chce usunąć."
    return create_homework_event(message)


def get_homework_events(message: Message, should_display_event_ids=False) -> tuple[bool, str or Embed]:
    read_data_file()
    amount_of_homeworks = len(homework_events)
    if amount_of_homeworks > 0:
        embed = Embed(title="Zadania", description=f"Lista zadań ({amount_of_homeworks}) jest następująca:")
    else:
        return False, f"{Emoji.info} Nie ma jeszcze żadnych zadań. " + \
               f"Możesz je tworzyć za pomocą komendy `{prefix}zadanie`."

    # Adds an embed field for each event
    for homework_event in homework_events:
        group_role_name = role_codes[homework_event.group]
        role_mention = "@everyone"  # Defaults to setting @everyone as the group the homework event is for
        if group_role_name != "everyone":
            # Adjusts the mention string if the homework event is not for everyone
            for role in message.guild.roles:
                if str(role) == group_role_name:
                    # Gets the role id from its name, sets the mention text to a discord mention using format <@&ID>
                    role_mention = f"<@&{role.id}>"
                    break
        if homework_event.reminder_is_active:
            # The homework hasn't been marked as completed yet
            event_reminder_hour = homework_event.reminder_date.split(' ')[1]
            if event_reminder_hour == '17':
                # The homework event hasn't been snoozed
                field_name = homework_event.deadline
            else:
                # Show an alarm clock emoji next to the event if it has been snoozed (reminder time is not 17:00)
                field_name = f"{homework_event.deadline} :alarm_clock: {event_reminder_hour}:00"
        else:
            # Show a check mark emoji next to the event if it has been marked as complete
            field_name = f"~~{homework_event.deadline}~~ :ballot_box_with_check:"

        field_value = f"**{homework_event.title}**\n"\
                      f"Zadanie dla {role_mention} (stworzone przez <@{homework_event.author_id}>)"
        if should_display_event_ids:
            field_value += f"\n*ID: event-id-{homework_event.id}*"
        embed.add_field(name=field_name, value=field_value, inline=False)
    embed.set_footer(text=f"Użyj komendy {prefix}zadania, aby pokazać tą wiadomość.")
    return True, embed


def create_homework_event(message: Message) -> tuple[bool, str]:
    args = message.content.split(" ")
    # Args is asserted to have at least 4 elements
    if args[1] == "del":
        user_inputted_id = args[2].replace("event-id-", '')
        try:
            deleted_event = delete_homework_event(int(user_inputted_id))
        except ValueError:
            return False, f":x: Nie znaleziono zadania z ID: `event-id-{user_inputted_id}`. " + \
                          f"Wpisz `{prefix}zadania`, aby otrzymać listę zadań oraz ich numery ID."
        return False, f"{Emoji.check} Usunięto zadanie z treścią: `{deleted_event}`"
    try:
        datetime.datetime.strptime(args[1], "%d.%m.%Y")
    except ValueError:
        return False, f"{Emoji.warning} Drugim argumentem komendy musi być data o formacie: `DD.MM.YYYY`."
    title = args[3]
    for word in args[4:]:
        title += " " + word
    author = message.author.id
    if args[2] == "@everyone":
        group_id = "grupa_0"
        group_text = ""
    else:
        # Removes redundant characters from the third argument in order to have just the numbers (role id)
        group_id = int(args[2].lstrip("<&").rstrip(">"))
        try:
            message.guild.get_role(group_id)
        except ValueError:
            return False, f"{Emoji.warning} Trzecim argumentem komendy musi być oznaczenie grupy, dla której jest zadanie."
        group_text = group_names[group_id] + " "

    new_event = HomeworkEvent(title, group_id, author, args[1] + " 17")
    if new_event.serialised in homework_events:
        return False, f"{Emoji.warning} Takie zadanie już istnieje."
    new_event.sort_into_container(homework_events)
    save_data_file()
    return False, f"{Emoji.check} Stworzono zadanie na __{args[1]}__ z tytułem: `{title}` {group_text}" + \
                  "z powiadomieniem na dzień przed o **17:00.**"


def delete_homework_event(event_id: int) -> str:
    """Delete a homework event with the given ID.
    Returns the title of the deleted event.

    Raises ValueError if an event with the given ID is not found.
    """
    for event in homework_events:
        if event.id == event_id:
            homework_events.remove(event)
            save_data_file()
            return event.title
    raise ValueError
