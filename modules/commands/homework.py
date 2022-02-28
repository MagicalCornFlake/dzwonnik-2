"""Module containing code relating to the 'zad' command."""

# Standard library imports
import datetime
import asyncio

# Third-party imports
from discord import Member, Message, Embed, Reaction

# Local application imports
from modules import bot, Emoji, data_manager, ROLE_CODES, GROUP_NAMES
from modules.commands import HomeworkEvent, homework_events


DESC = """Tworzy nowe zadanie i automatycznie ustawia powiadomienie na dzień przed.
    Jeśli w parametrach podane jest hasło 'del' oraz nr zadania, **zadanie to zostanie usunięte**.
    Parametry: __data__, __grupa__, __treść__ | 'del', __ID zadania__
    Przykłady:
    `{p}zad 31.12.2024 @Grupa 1 Zrób ćwiczenie 5` - stworzyłoby się zadanie na __31.12.2024__\
    dla grupy **pierwszej** z treścią: *Zrób ćwiczenie 5*.
    `{p}zad del 4` - usunęłoby się zadanie z ID: *event-id-4*."""
DESC_CREATE = "Wyświetla listę wszystkich zadań domowych utworzonych za pomocą komendy `{p}zad`."
DESC_LIST = "Alias komendy `{p}zadanie` lub `{p}zadania`, w zależności od podanych argumentów."


def process_homework_events_alias(message: Message) -> str or Embed:
    """Event handler for the 'zad' command."""
    args = message.content.split(" ")
    if len(args) == 1:
        return get_homework_events(message)
    return create_homework_event(message)


def get_homework_events(message: Message, with_event_ids=False) -> str or Embed:
    """Event handler for the 'zadania' command."""
    data_manager.read_data_file()
    amount_of_homeworks = len(homework_events)
    if amount_of_homeworks > 0:
        embed = Embed(
            title="Zadania", description=f"Lista zadań ({amount_of_homeworks}) jest następująca:")
    else:
        return (f"{Emoji.INFO} Nie ma jeszcze żadnych zadań. "
                f"Możesz je tworzyć za pomocą komendy `{bot.prefix}zadanie`.")

    # Adds an embed field for each event
    for homework_event in homework_events:
        group_role_name = ROLE_CODES[homework_event.group]
        # Defaults to setting @everyone as the group the homework event is for
        role_mention = "@everyone"
        if group_role_name != "everyone":
            # Adjusts the mention string if the homework event is not for everyone
            for role in message.guild.roles:
                if str(role) == group_role_name:
                    # Sets the role_mention variable to a valid Discord user mention string.
                    role_mention = f"<@&{role.id}>"
                    break
        if homework_event.reminder_is_active:
            # The homework hasn't been marked as completed yet
            event_reminder_hour = homework_event.reminder_date.split(' ')[1]
            if event_reminder_hour == '17':
                # The homework event hasn't been snoozed
                field_name = homework_event.deadline
            else:
                # Shows an alarm clock emoji next to the event if it has been snoozed.
                field_name = f"{homework_event.deadline} :alarm_clock: {event_reminder_hour}:00"
        else:
            # Show a check mark emoji next to the event if it has been marked as complete
            field_name = f"~~{homework_event.deadline}~~ :ballot_box_with_check:"

        field_value = f"**{homework_event.title}**\n"\
                      f"Zadanie dla {role_mention} (stworzone przez <@{homework_event.author_id}>)"
        if with_event_ids:
            field_value += f"\n*ID: event-id-{homework_event.event_id}*"
        embed.add_field(name=field_name, value=field_value, inline=False)
    embed.set_footer(
        text=f"Użyj komendy {bot.prefix}zadania, aby pokazać tą wiadomość.")
    return embed


def create_homework_event(message: Message) -> str:
    """Event handler for the 'zadanie' command."""
    args = message.content.split()
    if len(args) < 4:
        return (f"{Emoji.WARNING} Należy napisać po komendzie `{bot.prefix}zad` termin "
                f"oddania zadania, oznaczenie grupy, dla której jest zadanie oraz jego "
                f"treść, lub 'del' i ID zadania, którego się chce usunąć.")
    if args[1] == "del":
        user_inputted_id = args[2].replace("event-id-", '')
        try:
            deleted_event = delete_homework_event(int(user_inputted_id))
        except ValueError:
            msg = (f":x: Nie znaleziono zadania z ID: `event-id-{user_inputted_id}`. Wpisz"
                   f" `{bot.prefix}zadania`, aby otrzymać listę zadań oraz ich numery ID.")
        else:
            msg = f"{Emoji.CHECK} Usunięto zadanie z treścią: `{deleted_event}`"
        return msg
    try:
        datetime.datetime.strptime(args[1], "%d.%m.%Y")
    except ValueError:
        return f"{Emoji.WARNING} Pierwszym argumentem musi być data o formacie: `DD.MM.YYYY`."

    group_text: str = ""
    if args[2] == "@everyone":
        group_id = "grupa_0"
    else:
        # Removes redundant characters from the second argument in order to have just the role id
        group_id: str = ''.join(filter(str.isdigit, args[2]))
        try:
            role = message.guild.get_role(int(group_id))  # Can raise ValueError
            for group_code, role_name in ROLE_CODES.items():
                if role_name == str(role):
                    group_text = GROUP_NAMES[group_code] + " "
                    break
            else:
                raise KeyError
        except (ValueError, KeyError):
            bot.send_log("Invalid homework event group ID", group_id, force=True)
            return (f"{Emoji.WARNING} Drugim argumentem musi być oznaczenie grupy,"
                    f" dla której jest zadanie. Podana grupa jest niedozwolona.")
    title = " ".join(args[3:])
    new_event = HomeworkEvent(title, group_id, message.author.id, args[1] + " 17")
    if new_event.serialised in homework_events:
        return f"{Emoji.WARNING} Takie zadanie już istnieje."
    new_event.sort_into_container(homework_events)
    data_manager.save_data_file()
    return (f"{Emoji.CHECK} Stworzono zadanie na __{args[1]}__ z tytułem: `{title}`"
            f" {group_text}z powiadomieniem na dzień przed o **17:00.**")


def delete_homework_event(event_id: int) -> str:
    """Delete a homework event with the given ID.
    Returns the title of the deleted event.

    Raises ValueError if an event with the given ID is not found.
    """
    for event in homework_events:
        if event.event_id == event_id:
            homework_events.remove(event)
            data_manager.save_data_file()
            return event.title
    raise ValueError


async def wait_for_zadania_reaction(original_msg: Message, reply_msg: Message) -> None:
    """Callback function for the 'zadania' command.

    Reacts to the previously sent embedwith the detective emoji.
    If somebody else reacts with that emoji, it edits that embed to contain homework event IDs.
    """
    def check_for_valid_reaction(test_reaction: Reaction, reaction_author: Member) -> bool:
        """Util function for validating the reaction.
        Returns a boolean indicating if the emoji was correct and the user was someone else."""
        reaction_valid = str(test_reaction.emoji) == Emoji.UNICODE_DETECTIVE
        return reaction_valid and reaction_author != bot.client.user

    await reply_msg.add_reaction(Emoji.UNICODE_DETECTIVE)
    try:
        await bot.client.wait_for('reaction_add', timeout=10.0, check=check_for_valid_reaction)
    except asyncio.TimeoutError:
        # 10 seconds have passed with no user input
        await reply_msg.clear_reactions()
    else:
        # Someone has added detective reaction to message
        await reply_msg.clear_reactions()
        await reply_msg.edit(embed=get_homework_events(original_msg, True))
