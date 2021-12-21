"""Dzwonnik 2, a Discord bot, by Konrad Guzek."""

# Standard library imports
import asyncio
import datetime
import importlib
import json
import math
import os
import traceback

# Third-party imports
import discord
import discord.ext.tasks

# Local application imports
from modules import file_management
from modules.constants import *
from modules.util import web_api
from modules.util.api import steam_api, lucky_numbers_api
from modules.util.crawlers import plan_crawler, substitutions_crawler


intents = discord.Intents.default()
intents.members = True
client = discord.Client(intents=intents)
my_server = client.get_guild(766346477874053130)  # 2D The Supreme server

# This method is called when the bot comes online
@client.event
async def on_ready() -> None:
    global my_server

    guilds = {guild.id: guild.name for guild in client.guilds}
    log_message(f"Successfully logged in as {client.user}\nActive guilds:", guilds, force=True)
    my_server = client.get_guild(my_server_id)

    # Sets status message on bot start
    status = discord.Activity(type=discord.ActivityType.watching, name=get_new_status_msg())
    await client.change_presence(activity=status)

    # Starts loops that run continuously
    track_time_changes.start()
    track_api_updates.start()

    # Checks if the bot was just restarted
    for channel_id in [ChannelID.bot_testing, ChannelID.bot_logs]:
        channel = client.get_channel(channel_id)
        try:
            last_test_message = await channel.fetch_message(channel.last_message_id)
        except discord.errors.NotFound:
            log_message(f"Could not find last message in channel {channel.name}. It was probably deleted.")
        else:
            if last_test_message is None:
                log_message(f"Last message in channel {channel.name} is None.")
            elif last_test_message.author == client.user:
                if last_test_message.content == "Restarting bot...":
                    await last_test_message.edit(content="Restarted bot!")
            else:
                log_message(f"Last message in channel {channel.name} was not sent by me.")


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
                log_message(f"Removing obsolete event '{event.title}' from container")
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


# noinspection SpellCheckingInspection
lesson_details: dict = {
    # "ang-1": {"name": "język angielski", "link": "lookup/bpwq26lzht"},
    # "ang-2": {"name": "język angielski", "link": "lookup/fbrsxfud26"},
    # "ang-kw": {"name": "język angielski z p. Kwiatkowską", "link": "lookup/bgz74rwodu"},
    # "bio": {"name": "biologia", "link": "lookup/bhaw4bkiwa"},
    # "bio-1": {"name": "biologia", "link": "lookup/bhaw4bkiwa"},
    # "bio-2": {"name": "biologia", "link": "lookup/bhaw4bkiwa"},
    # "bio-roz": {"name": "biologia rozszerzona", "link": ""},
    # "chem": {"name": "chemia", "link": "lookup/ccydofjmsy"},
    # "chem-1": {"name": "chemia", "link": "lookup/ccydofjmsy"},
    # "chem-2": {"name": "chemia", "link": "lookup/ccydofjmsy"},
    # "chem-roz": {"name": "chemia rozszerzona", "link": ""},
    # "de-1": {"name": "język niemiecki", "link": "otb-miyx-xfw"},
    # "de-2": {"name": "język niemiecki", "link": "lookup/ggm2fxojv6"},
    # "dram": {"name": "drama", "link": "lookup/dzhxxxfabz"},
    # "edb": {"name": "edukacja dla bezpieczeństwa", "link": "lookup/daw4tvxftt"},
    # "es": {"name": "język hiszpański", "link": "fpv-tduz-ptc"},
    # "fiz": {"name": "fizyka", "link": "lookup/exacwjtr67"},
    # "fiz-roz": {"name": "fizyka rozszerzona", "link": ""},
    # "fr": {"name": "język francuski", "link": "xwa-ahgy-wns"},
    # "geo": {"name": "geografia", "link": "lookup/dzuekigxx3"},
    # "geo-roz": {"name": "geografia rozszerzona", "link": ""},
    # "gw": {"name": "godzina wychowawcza", "link": ""},
    # "his": {"name": "historia", "link": "lookup/e5elwpevj5"},
    # "his-roz": {"name": "historia rozszerzona", "link": ""},
    # "inf": {"name": "informatyka", "link": "lookup/f7mwatesda"},
    # "mat": {"name": "matematyka", "link": ""},
    # "mat-roz": {"name": "matematyka rozszerzona", "link": ""},
    # "plas-1": {"name": "plastyka", "link": ""},
    # "plas-2": {"name": "plastyka", "link": ""},
    # "przed": {"name": "przedsiębiorczość", "link": ""},
    # "pol": {"name": "język polski", "link": "lookup/fthvbikyap"},
    # "rel": {"name": "religia", "link": "lookup/h2g6dftul7"},
    # "tok": {"name": "theory of knowledge", "link": "lookup/dpvw6r3mg7"},
    # "wf": {"name": "wychowanie fizyczne", "link": "lookup/gb75o2kzx4"},
    # "wos": {"name": "wiedza o społeczeństwie", "link": "lookup/flikhkjfkr"}
}
prefix = '!'  # Prefix used before commands
enable_log_messages = True
use_bot_testing = False
homework_events = HomeworkEventContainer()
tracked_market_items = []
restart_on_exit = True
current_period: int = 0
lesson_plan: dict = plan_crawler.get_lesson_plan("2d", True)



def populate_lesson_details():
    lesson_names = []
    for item in lesson_plan:
        if item not in weekday_names:
            continue
        for period in item:
            for lesson in period:
                lesson_names.append(lesson["name"])
    lesson_names.sort()
    for lesson in lesson_names:
        lesson_details[lesson] = { "name": lesson, "link": "" }

populate_lesson_details()


def get_formatted_period_time(period: int) -> str:
    times: list[list[int]] = lesson_plan["Godz"][period]
    # e.g. [[8, 0], [8, 45]] -> "08:00-08:45"
    return "-".join([':'.join([f"{t:02}" for t in time]) for time in times])


def read_data_file(filename: str = "data.json") -> None:
    global homework_events
    # Reads data file and updates settings
    if not os.path.isfile(filename):
        with open(filename, 'w') as file:
            default_settings = {
                # lesson_details is updated later anyway, so we can leave it empty.
                "lesson_details": {},
                "homework_events": {},
                "tracked_market_items": [],
                "lucky_numbers": lucky_numbers_api.cached_data
            }
            json.dump(default_settings, file, indent=2)
    with open(filename, 'r') as file:
        data = json.load(file)
    # We have defined lesson_details above, but this replaces any values that are different than the default
    if "lesson_details" in data:
        lesson_details.update(data["lesson_details"])
    # homework_events.clear()  # To ensure there aren't any old instances, not 100% needed though
    # Creates new instances of the HomeworkEvent class with the data from the file
    new_event_candidates = HomeworkEventContainer()
    for event_id in data["homework_events"]:
        attributes = data["homework_events"][event_id]
        title, group, author_id, deadline, reminder_date, reminder_is_active = [attributes[attr] for attr in attributes]
        new_event_candidate = HomeworkEvent(title, group, author_id, deadline, reminder_date, reminder_is_active)
        new_event_candidates.append(new_event_candidate)
    homework_events.remove_disjunction(new_event_candidates)
    for new_event_candidate in new_event_candidates:
        if new_event_candidate.serialised not in homework_events.serialised:
            new_event_candidate.sort_into_container(homework_events)
    for item_attributes in data["tracked_market_items"]:
        item_name, min_price, max_price, author_id = [item_attributes[attr] for attr in item_attributes]
        item = TrackedItem(item_name, min_price, max_price, author_id)
        if item not in tracked_market_items:
            tracked_market_items.append(item)
    lucky_numbers_api.cached_data = data["lucky_numbers"]


def save_data_file(filename: str = "data.json", should_log: bool = True) -> None:
    """Saves the settings stored in the program's memory to the file provided.

    Arguments:
        filename -- the name of the file relative to the program root directory to write to (default 'data.json').
        should_log -- whether or not the save should be logged in the Discord Log and in the console.
    """
    if should_log:
        log_message("Saving data file", filename)
    # Creates containers with the data to be saved in .json format
    serialised_homework_events = {event.id_string: event.serialised for event in homework_events}
    serialised_tracked_market_items = [item.serialised for item in tracked_market_items]
    # Creates a parent dictionary to save all data that needs to be saved
    data_to_be_saved = {
        "lesson_details": lesson_details,
        "homework_events": serialised_homework_events,
        "tracked_market_items": serialised_tracked_market_items,
        "lucky_numbers": lucky_numbers_api.cached_data
    }

    # Replaces file content with new data
    with open(filename, 'w') as file:
        json.dump(data_to_be_saved, file, indent=2)
    if should_log:
        log_message(f"Successfully saved data file '{filename}'.")


def get_new_status_msg(query_time: datetime.datetime = None) -> str:
    """Determine the current lesson status message.
    
    Arguments:
        query_time -- the time to get the status for.
    """
    global current_period
    if query_time is None:
        # Default time to check is current time
        query_time = datetime.datetime.now()
    log_message(f"Updating bot status ...")
    next_period_is_today, next_period, next_lesson_weekday = get_next_period(query_time)
    if next_period_is_today:
        current_period = next_period % 10
        lesson_start_time, lesson_end_time = get_formatted_period_time(current_period).split('-')
        if next_period < 10:
            # Currently break time
            new_status_msg = "przerwa do " + lesson_start_time
        else:
            # Currently lesson
            msgs: dict[str, str] = {}  # Dictionary with lesson group code and lesson name
            for role_code in list(role_codes.keys())[1:]:
                lesson = get_lesson_by_roles(current_period, next_lesson_weekday, [role_code])
                if not lesson:
                    # No lesson for that group
                    continue
                lesson_info, group_code = lesson[:2]
                msgs[group_code] = lesson_info['name']
                # Found lesson for 'grupa_0' (whole class)
                if group_code == "grupa_0":
                    log_message("Found lesson for entire class, skipping checking individual groups.")
                    break
            # set(msgs.values()) returns a list of unique lesson names
            lesson_text = "/".join(set(msgs.values()))
            group_name = list(msgs.keys())[0]
            if len(msgs) == 1 and group_name != "grupa_0":
                # Specify the group the current lesson is for if only one group has it
                lesson_text += " " + group_names[group_name]
            new_status_msg = f"{lesson_text} do {lesson_end_time}"
    else:
        # After the last lesson for the given day
        current_period = -1
        new_status_msg = "koniec lekcji!" if query_time.weekday() < Weekday.friday else "weekend!"
    log_message(f"... new status message is '{new_status_msg}'.")
    return new_status_msg


async def remind_about_homework_event(event: HomeworkEvent, tense: str) -> None:
    mention_text = "@everyone"  # To be used at the beginning of the reminder message
    event_name = event.title
    for role in role_codes:
        if role == event.group:
            mention_role = discord.utils.get(my_server.roles, name=role_codes[role])
            if role != "grupa_0":
                mention_text = my_server.get_role(mention_role.id).mention
            break
    target_channel = client.get_channel(ChannelID.bot_testing if use_bot_testing else ChannelID.nauka)
    # Which tense to use in the reminder message
    when = {
        "today": "dziś jest",
        "tomorrow": "jutro jest",
        "past": f"{event.deadline} było",
        "future": f"{event.deadline} jest"  # 'future' is not really needed but I added it cause why not
    }[tense]  # tense can have a value of 'today', 'tomorrow' or 'past'
    message = await target_channel.send(f"{mention_text} Na {when} zadanie: **{event_name}**.")
    emojis = [Emoji.unicode_check, Emoji.unicode_alarm_clock]
    for emoji in emojis:
        await message.add_reaction(emoji)

    def check_for_valid_reaction(test_reaction, reaction_user):
        return reaction_user != client.user and str(test_reaction.emoji) in emojis

    async def snooze_event():
        new_reminder_time = datetime.datetime.now() + datetime.timedelta(hours=1)
        event.reminder_date = new_reminder_time.strftime("%d.%m.%Y %H")
        await message.edit(content=":alarm_clock: Przełożono powiadomienie dla zadania `" +
                                   f"{event_name}` na {str(new_reminder_time.hour).zfill(2)}:00.")

    try:
        reaction, user = await client.wait_for('reaction_add', timeout=120.0, check=check_for_valid_reaction)
    except asyncio.TimeoutError:  # 120 seconds have passed with no user input
        await snooze_event()
    else:
        if str(reaction.emoji) == emojis[0]:
            # Reaction emoji is ':ballot_box_with_check:'
            event.reminder_is_active = False
            await message.edit(content=f":ballot_box_with_check: Zaznaczono zadanie `{event_name}` jako odrobione.")
        else:  # Reaction emoji is :alarm_clock:
            await snooze_event()
    await message.clear_reactions()
    save_data_file()  # Updates data.json so that if the bot is restarted the event's parameters are saved


@discord.ext.tasks.loop(seconds=1)
async def track_time_changes() -> None:
    current_time = datetime.datetime.now()  # Today's time
    tomorrow = datetime.date.today() + datetime.timedelta(days=1)  # Today's date + 1 day
    # Checks if current time is in list of key times
    if [current_time.hour, current_time.minute] in lesson_plan["Godz"] and current_time.second == 0:
        # Check is successful, bot updates Discord status
        status = discord.Activity(type=discord.ActivityType.watching, name=get_new_status_msg())
        await client.change_presence(activity=status)
    # Checks if the bot should make a reminder about due homework
    for event in homework_events:
        reminder_time = datetime.datetime.strptime(event.reminder_date, "%d.%m.%Y %H")
        event_time = datetime.datetime.strptime(event.deadline, "%d.%m.%Y")
        # If this piece of homework has already had a reminder issued, ignore it
        if not event.reminder_is_active or reminder_time > current_time:
            continue
        if event_time.date() > tomorrow:
            tense = "future"
        elif event_time.date() == tomorrow:
            tense = "tomorrow"
        elif event_time.date() == current_time.date():
            tense = "today"
        else:
            tense = "past"
        await remind_about_homework_event(event, tense)


@discord.ext.tasks.loop(minutes=1)
async def track_api_updates() -> None:
    for item in tracked_market_items:
        await asyncio.sleep(3)
        result = steam_api.get_item(item.name)
        price = steam_api.get_item_price(result)
        # Strips the price string of any non-digit characters and returns it as an integer
        price = int(''.join([char if char in "0123456789" else '' for char in price]))
        if item.min_price < price < item.max_price:
            continue
        target_channel = client.get_channel(ChannelID.bot_testing if use_bot_testing else ChannelID.admini)
        await target_channel.send(f":moneybag: Uwaga, <@{item.author_id}>! "
                                  f"Przedmiot *{item.name}* kosztuje teraz **{price/100:.2f}zł**.")
        tracked_market_items.remove(item)
        save_data_file()
    await asyncio.sleep(3)
    # Update the lucky numbers cache, and if it's changed, announce the new numbers in the specified channel.
    try:
        old_cache = lucky_numbers_api.update_cache()
    except web_api.InvalidResponseException as e:
        # Ping @Konrad
        await client.get_channel(ChannelID.bot_logs).send(f"<@{member_ids[8 - 1]}>")
        log_message(f"Error! Received an invalid response from the web request (cache update). Exception trace:\n" +
                    ''.join(traceback.format_exception(type(e), e, e.__traceback__)))
    else:
        if old_cache != lucky_numbers_api.cached_data:
            log_message(f"New lucky numbers data!")
            target_channel = client.get_channel(ChannelID.bot_testing if use_bot_testing else ChannelID.general)
            await target_channel.send(embed=get_lucky_numbers_embed()[1])
            save_data_file()


@track_api_updates.before_loop
@track_time_changes.before_loop
async def wait_until_ready_before_loops() -> None:
    await client.wait_until_ready()


# # Times for the start and end of each period (0-9)
# timetable = [
#     "07:10-07:55",  # Period 0
#     "08:00-08:45",  # Period 1
#     "08:50-09:35",  # Period 2
#     "09:45-10:30",  # Period 3
#     "10:40-11:25",  # Period 4
#     "11:35-12:20",  # Period 5
#     "12:50-13:35",  # Period 6
#     "13:40-14:25",  # Period 7
#     "14:30-15:15",  # Period 8
#     "15:20-16:05"   # Period 9
# ]

# # List of times bot should update status for
# watch_times = [time.split("-")[i] for time in timetable for i in range(2)]

# # The following are timetables for each day
# # Format: [lesson code, group ID, period]
# lessons_monday = [
#     ["bio", "grupa_0", 1],
#     ["mat", "grupa_0", 2],
#     ["wf", "grupa_0", 3],
#     ["wf", "grupa_0", 4],
#     ["ang-1", "grupa_1", 5],
#     ["ang-2", "grupa_2", 5],
#     ["pol", "grupa_0", 6],
#     ["pol", "grupa_0", 7],
#     ["rel", "grupa_rel", 8],
#     ["rel", "grupa_rel", 9]
# ]

# lessons_tuesday = [
#     ["his", "grupa_0", 1],
#     ["ang-1", "grupa_1", 2],
#     ["ang-kw", "grupa_2", 2],
#     ["ang-1", "grupa_1", 3],
#     ["ang-2", "grupa_2", 3],
#     ["pol", "grupa_0", 4],
#     ["pol", "grupa_0", 5],
#     ["mat", "grupa_0", 6],
#     ["mat", "grupa_0", 7],
#     ["tok", "grupa_0", 8]
# ]

# lessons_wednesday = [
#     ["geo", "grupa_0", 2],
#     ["mat", "grupa_0", 3],
#     ["chem", "grupa_0", 4],
#     ["pol", "grupa_0", 5],
#     ["pol", "grupa_0", 6],
#     ["inf", "grupa_1", 7],
#     ["ang-2", "grupa_2", 7],
#     ["inf", "grupa_1", 8],
#     ["ang-2", "grupa_2", 8]
# ]

# lessons_thursday = [
#     ["przed", "grupa_0", 1],
#     ["chem", "grupa_1", 2],
#     ["bio", "grupa_2", 2],
#     ["bio", "grupa_1", 3],
#     ["ang-2", "grupa_2", 3],
#     ["his", "grupa_0", 4],
#     ["wos", "grupa_0", 5],
#     ["geo", "grupa_0", 6],
#     ["wf", "grupa_0", 7],
#     ["fiz", "grupa_0", 8]
# ]

# lessons_friday = [
#     ["chem", "grupa_2", 1],
#     ["gw", "grupa_0", 2],
#     ["ang-1", "grupa_1", 3],
#     ["inf", "grupa_2", 3],
#     ["ang-1", "grupa_1", 4],
#     ["inf", "grupa_2", 4],
#     ["fr", "grupa_fr", 5],
#     ["es", "grupa_es", 5],
#     ["de-1", "grupa_de1", 5],
#     ["de-2", "grupa_de2", 5],
#     ["fr", "grupa_fr", 6],
#     ["es", "grupa_es", 6],
#     ["de-1", "grupa_de1", 6],
#     ["de-2", "grupa_de2", 6],
#     ["mat", "grupa_0", 7],
#     ["ang-kw", "grupa_1", 8],
#     ["dram", "grupa_2", 8],
#     ["dram", "grupa_1", 9]
# ]


def create_homework_event(message: discord.Message) -> tuple[bool, str]:
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
            return False, ":warning: Trzecim argumentem komendy musi być oznaczenie grupy, dla której jest zadanie."
        group_text = group_names[group_id] + " "

    new_event = HomeworkEvent(title, group_id, author, args[1] + " 17")
    if new_event.serialised in homework_events:
        return False, f":warning: Takie zadanie już istnieje."
    new_event.sort_into_container(homework_events)
    save_data_file()
    return False, f":white_check_mark: Stworzono zadanie na __{args[1]}__ z tytułem: `{title}` {group_text}" + \
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


def get_homework_events(message: discord.Message, should_display_event_ids=False) -> tuple[bool, str or discord.Embed]:
    read_data_file()
    amount_of_homeworks = len(homework_events)
    if amount_of_homeworks > 0:
        embed = discord.Embed(title="Zadania", description=f"Lista zadań ({amount_of_homeworks}) jest następująca:")
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


def process_homework_events_alias(message: discord.Message) -> tuple[bool, str or discord.Embed]:
    args = message.content.split(" ")
    if len(args) == 1:
        return get_homework_events(message)
    elif len(args) < 4:
        return False, f":warning: Należy napisać po komendzie `{prefix}zad` termin oddania zadania, oznaczenie " + \
            "grupy, dla której jest zadanie oraz jego treść, lub 'del' i ID zadania, którego się chce usunąć."
    return create_homework_event(message)


def update_meet_link(message: discord.Message) -> tuple[bool, str]:
    args = message.content.split(" ")
    if len(args) != 1:
        if args[1] in lesson_details:
            if len(args) == 2:
                lesson, link = lesson_details[args[1]].values()
                return False, f"{Emoji.info} Link do Meeta dla lekcji " + \
                    f"'__{lesson}__' to <https://meet.google.com/{link}?authuser=0&hs=179>."
            else:
                if not message.channel.permissions_for(message.author).administrator:
                    return False, ":warning: Nie posiadasz uprawnień do zmieniania linków Google Meet."
                link_is_dash_format = len(args[2]) == 12 and args[2][3] == args[2][8] == "-"
                link_is_lookup_format = len(args[2]) == 17 and args[2].startsWith("lookup/")
                if link_is_dash_format or link_is_lookup_format:
                    # User-given link is valid
                    old_link = lesson_details[args[1]]["link"]
                    lesson_details[args[1]]["link"] = args[2]
                    save_data_file()
                    return False, f":white_check_mark: Zmieniono link dla lekcji " \
                                  f"'__{lesson_details[args[1]]['name']}__' z `{old_link}` na **{args[2]}**."
    msg = f"Należy napisać po komendzie `{prefix}meet` kod lekcji, " + \
        "aby zobaczyć jaki jest ustawiony link do Meeta dla tej lekcji, " + \
        "albo dopisać po kodzie też nowy link aby go zaktualizować.\nKody lekcji:```md"
    for code, info_dict in lesson_details.items():
        msg += f"\n# {code} [{info_dict['name']}]({info_dict['link']})"
    # noinspection SpellCheckingInspection
    msg += "```\n:warning: Uwaga: link do Meeta powinien mieć formę `xxx-xxxx-xxx` bądź `lookup/xxxxxxxxxx`."
    return False, msg


def get_help_message(_message: discord.Message) -> tuple[bool, discord.Embed]:
    embed = discord.Embed(title="Lista komend", description=f"Prefiks dla komend: `{prefix}`")
    for command_name, command_description in command_descriptions.items():
        if command_description is None:
            continue
        embed.add_field(name=command_name, value=command_description.format(p=prefix), inline=False)
    embed.set_footer(text=f"Użyj komendy {prefix}help lub mnie @oznacz, aby pokazać tą wiadomość.")
    return True, embed


def get_lesson_plan(message: discord.Message) -> tuple[bool, str or discord.Embed]:
    args = message.content.split(" ")
    today = datetime.datetime.now().weekday()
    if len(args) == 1:
        query_day = today if today < Weekday.saturday else Weekday.monday
    else:
        query_day = -1
        try:
            # This 'try' clause raises RuntimeError if the input is invalid for whatever reason
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
        except RuntimeError as e:
            log_message(f"Handling exception with args: '{' '.join(args[1:])}' ({type(e).__name__}: \"{e}\")")
            return False, f"{Emoji.warning} Należy napisać po komendzie `{prefix}plan` numer dnia (1-5) " \
                          f"bądź dzień tygodnia, lub zostawić parametry komendy puste."

    plan = lesson_plan[weekday_names[query_day]]

    # The generator expression creates a list that maps each element from 'plan' to the boolean it evaluates to.
    # Empty lists are evaluated as False, non-empty lists are evaluated as True.
    # The sum() function adds the contents of the list, keeping in mind that True == 1 and False == 0.
    # In essence, 'periods' evaluates to the number of non-empty lists in 'plan' (i.e. the number of lessons on that day).
    periods: int = sum([bool(lesson) for lesson in plan])
    first_period: int = 0

    desc = f"Plan lekcji na **{weekday_names[query_day].lower().replace('środa', 'środę')}** ({periods} lekcji) jest następujący:"
    embed = discord.Embed(title="Plan lekcji", description=desc)
    embed.set_footer(text=f"Użyj komendy {prefix}plan, aby pokazać tą wiadomość.")

    for period in lesson_plan["Nr"]:
        if not plan[period]:
            # No lesson for the current period
            first_period += 1
            continue
        for lesson in plan[period]:
            text = f"Sala {lesson['room_id']} — " if "room_id" in lesson else ""
            name = lesson["name"]
            link = None
            if link:
                text += f"[{name}](https://meet.google.com/{link}?authuser=0&hs=179) "
            else:
                text += f"[{name}](http://guzek.uk/error/404?lang=pl-PL&source=discord) "
            if lesson['group'] != "grupa_0":
                text += f"({group_names[lesson['group']]})"
            if period < first_period + periods:
                text += "\n"
        txt = f"Lekcja {period} ({get_formatted_period_time(period)})"
        is_current_lesson = query_day == today and period == current_period 
        embed.add_field(name=f"*{txt}    <── TERAZ*" if is_current_lesson else txt, value=text, inline=False)
    return True, embed


def get_next_period(given_time: datetime.datetime) -> tuple[bool, float, list[list[dict[str, str]]]]:
    """Get the information about the next period for a given time.

    Arguments:
        given_time -- the start time to base the search off of.

    Returns a tuple consisting of a boolean indicating if that day is today, the period number, and the day of the week.
    If the current time is during a lesson, the period number will be incremented by 10.
    """
    log_message(f"Getting next period for {given_time:%d/%m/%Y %X} ...")
    current_day_index: int = given_time.weekday()

    if current_day_index < Weekday.saturday:
        for period, times in enumerate(lesson_plan["Godz"]):
            print("times:", times)
            for is_lesson, time in enumerate(times):
                print("time:", time)
                hour, minute = time
                if given_time.hour < hour and given_time.minute < minute:
                    log_message(f"... this is before {hour:02}:{minute:02} (period {period}).")
                    return True, current_day_index, period + 10 * is_lesson
        # Could not find any such lesson.
        # current_day_index == Weekday.friday == 4  -->  next_school_day == (current_day_index + 1) % Weekday.saturday == (4 + 1) % 5 == 0 == Weekday.monday
        next_school_day = (current_day_index + 1) % Weekday.saturday
    else:
        next_school_day = Weekday.monday

    # If it's currently weekend or after the last lesson for the day
    log_message(f"... there are no more lessons today. Next school day: {next_school_day}")
    for first_period, lessons in enumerate(lesson_plan[next_school_day]):
        # Stop incrementing 'first_period' when the 'lessons' object is a non-empty list
        if lessons:
            break
    return False, first_period, next_school_day


def get_lesson_by_roles(query_period: int, weekday_index: int, roles: list[str, discord.Role]) -> \
        tuple[dict[str, str], str] or False:
    """Get the lesson details for a given period, day and user roles list.
    Arguments:
        query_period -- the period number to look for.
        weekday_index -- the index of the weekday to look at.
        roles -- the roles of the user that the lesson is defined to be intended for.

    Returns a tuple containing the lesson details and the code of the group.
    """
    target_roles = ["grupa_0"] + [str(role) for role in roles if role in role_codes or str(role) in role_codes.values()]
    log_message("Looking for lesson with roles:", target_roles)
    for lesson in lesson_plan[weekday_names[weekday_index]][query_period]:
        group_code = lesson["group"]
        if group_code in target_roles or role_codes[group_code] in target_roles:
            log_message(f"Found lesson '{lesson['name']}' on period {query_period}.")
            return lesson_details[lesson["name"]], group_code
    log_message(f"Did not find a lesson matching those roles for period {query_period} on day {weekday_index}.", force=True)
    return False


def get_datetime_from_input(message: discord.Message, calling_command: str) -> tuple[bool, str or datetime.datetime]:
    args = message.content.split(" ")
    current_time = datetime.datetime.now()
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


def get_time(period: int, base_time: datetime.datetime, get_period_end_time: bool) -> tuple[str, datetime.datetime]:
    times = lesson_plan["Godz"][period]
    hour, minute = times[get_period_end_time]
    date_time = base_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
    return date_time


def conjugate_seconds_to_minutes(seconds: int) -> str:
    num = math.ceil(seconds / 60)
    if num == 1:
        return f"1 minutę"
    last_digit: int = int(str(num)[-1])
    if 1 < last_digit < 5 and num not in [12, 13, 14]:
        return f"{num} minuty"
    else:
        return f"{num} minut"


# Returns the message to send when the user asks for the next lesson
def get_next_lesson(message: discord.Message) -> tuple[bool, str or discord.Embed]:
    success, result = get_datetime_from_input(message, 'nl')
    if not success:
        return False, result
    current_time: datetime.datetime = result

    def process(time: datetime.datetime) -> tuple[bool, str, str]:
        next_lesson_is_today, lesson_period, weekday_index = get_next_period(time)
        actual_period = lesson_period % 10
        lesson = get_lesson_by_roles(actual_period, weekday_index, message.author.roles)
        if not lesson:
            return False, f":x: Nie ma żadnych zajęć dla Twojej grupy na {actual_period}-ej lekcji.", ""
        lesson_info, group_code = lesson
        if next_lesson_is_today:
            if actual_period != lesson_period:
                # Currently lesson
                lesson_end_datetime = get_time(actual_period, current_time, True)
                # Get the next lesson after the end of this one, recursive call
                return process(lesson_end_datetime)
            # Currently break
            when = " "
            lesson_start_datetime = get_time(actual_period, current_time, False)
            countdown = f" (za {conjugate_seconds_to_minutes((lesson_start_datetime - current_time).seconds)})"
        else:
            when = " w poniedziałek" if Weekday.friday <= current_time.weekday() <= Weekday.saturday else " jutro"
            countdown = ""
        next_period_time = get_formatted_period_time(actual_period).split("-")[0]
        group = group_names[group_code] + " " * (group_code != "grupa_0")
        return True, f"{Emoji.info} Następna lekcja {group}to **{lesson_info['name']}**" \
                     f"{when} o godzinie __{next_period_time}__{countdown}.", lesson_info['link']

    success, msg, link = process(current_time)
    if not success:
        return False, msg

    embed = discord.Embed(title=f"Następna lekcja ({current_time:%H:%M})", description=msg)
    embed.add_field(name="Link do lekcji", value=f"[meet.google.com](https://meet.google.com/{link}?authuser=0&hs=179)")
    embed.set_footer(text=f"Użyj komendy {prefix}nl, aby pokazać tą wiadomość.")
    return True, embed


# Calculates the time of the next break
def get_next_break(message: discord.Message) -> tuple[bool, str]:
    success, result = get_datetime_from_input(message, 'nb')
    if not success:
        return False, result
    current_time: datetime.datetime = result

    next_period_is_today, lesson_period = get_next_period(current_time)[:2]

    if next_period_is_today:
        break_start_time, break_start_datetime = get_time(lesson_period % 10, current_time, True)
        break_countdown = break_start_datetime - current_time
        minutes = conjugate_seconds_to_minutes(break_countdown.seconds)
        msg = f"{Emoji.info} Następna przerwa jest za {minutes} o __{break_start_time}"
        more_lessons_today, next_period = get_next_period(break_start_datetime)[:2]
        log_message("More lessons today:", more_lessons_today)
        if more_lessons_today:
            break_end_time, break_end_datetime = get_time(next_period, break_start_datetime, False)
            break_length = break_end_datetime - break_start_datetime
            msg += f"—{break_end_time}__ ({break_length.seconds // 60} min)."
        else:
            msg += "__ i jest to ostatnia przerwa."
    else:
        msg = f"{Emoji.info} Już jest po lekcjach!"
    return False, msg


def get_web_api_error_message(e: Exception) -> str:
    if type(e) is web_api.InvalidResponseException:
        return f"Nastąpił błąd w połączeniu: {e.status_code}"
    if type(e) is web_api.TooManyRequestsException:
        return f"Musisz poczekać jeszcze {web_api.max_request_cooldown - e.time_since_last_request:.2f}s."
    if type(e) is steam_api.NoSuchItemException:
        return f":x: Nie znaleziono przedmiotu `{e.query}`. Spróbuj ponownie i upewnij się, że nazwa się zgadza."
    else:
        raise e


# Returns the message to send when the user asks for the price of an item on the Steam Community Market
def get_market_price(message: discord.Message, result_override=None) -> tuple[bool, str]:
    args: str = message.content.lstrip(f"{prefix}cena ").split(" waluta=") if result_override is None else [message]
    currency = args[-1] if len(args) > 1 else 'PLN'
    try:
        result = steam_api.get_item(args[0], 730, currency) if result_override is None else result_override
        return False, f"{Emoji.info} Aktualna cena dla *{args[0]}* to `{steam_api.get_item_price(result)}`."
    except Exception as e:
        return False, get_web_api_error_message(e)


# Returns the message to send when the user wishes to track an item on the Steam Community Market
def start_market_tracking(message: discord.Message):
    # noinspection SpellCheckingInspection
    args = message.content.lstrip(f"{prefix}sledz ").split(" min=")
    min_price = args[-1].split(" max=")[0].strip()
    max_price = args[-1].split(" max=")[-1].strip()
    try:
        min_price = int(float(min_price) * 100)
        max_price = int(float(max_price) * 100)
    except ValueError:
        # noinspection SpellCheckingInspection
        return False, f"{Emoji.warning} Należy wpisać po nazwie przedmiotu cenę minimalną oraz cenę maksymalną. " \
                      f"Przykład: `{prefix}sledz Operation Broken Fang Case min=1 max=3`."
    else:
        item_name = args[0].rstrip()
        try:
            result = steam_api.get_item(item_name)
        except Exception as e:
            return False, get_web_api_error_message(e)
        else:
            author_id = message.author.id
            item = TrackedItem(item_name, min_price, max_price, author_id)
            if item in tracked_market_items:
                for item in tracked_market_items:
                    if item.name.lower() == item_name.lower():
                        return False, f"{Emoji.warning} Przedmiot *{item.name}* jest już śledzony przez " + \
                               (f"użytkownika <@{item.author_id}>." if item.author_id != author_id else "Ciebie.")
            tracked_market_items.append(item)
            save_data_file()
            return False, f"{Emoji.check} Stworzono zlecenie śledzenia przedmiotu *{item_name}* w przedziale " \
                          f"`{min_price/100:.2f}zł - {max_price/100:.2f}zł`.\n" + \
                get_market_price(item_name, result_override=result)[1]


def stop_market_tracking(message: discord.Message) -> tuple[bool, str]:
    # noinspection SpellCheckingInspection
    item_name = message.content.lstrip(f"{prefix}odsledz ")
    for item in tracked_market_items:
        if item.name.lower() == item_name.lower():
            if item.author_id == message.author.id or message.channel.permissions_for(message.author).administrator:
                tracked_market_items.remove(item)
                save_data_file()
                return False, f"{Emoji.check} Zaprzestano śledzenie przedmiotu *{item.name}*."
            return False, f":x: Nie jesteś osobą, która zażyczyła śledzenia tego przedmiotu."
    return False, f":x: Przedmiot *{item_name}* nie jest aktualnie śledziony."


def get_lucky_numbers_embed(*_message: tuple[discord.Message]) -> tuple[bool, discord.Embed or str]:
    try:
        data = lucky_numbers_api.get_lucky_numbers()
    except Exception as e:
        log_message(f"Error! Received an invalid response from the web request. Exception trace:\n" +
                    ''.join(traceback.format_exception(type(e), e, e.__traceback__)))
        return False, get_web_api_error_message(e)
    msg = f"Szczęśliwe numerki na {data['date']}:"
    embed = discord.Embed(title="Szczęśliwe numerki", description=msg)
    for n in data["luckyNumbers"]:
        member_text = f"*W naszej klasie nie ma osoby z numerkiem __{n}__.*" if n > len(member_ids) else \
            f"<@!{member_ids[n - 1]}>" if type(member_ids[n - 1]) is int else member_ids[n - 1]
        embed.add_field(name=n, value=member_text, inline=False)
    # embed.add_field(name="\u200B", value="\u200B", inline=False)
    excluded_classes = ", ".join(data["excludedClasses"]) if len(data["excludedClasses"]) > 0 else "*Brak*"
    embed.add_field(name="Wykluczone klasy", value=excluded_classes, inline=False)
    embed.set_footer(text=f"Użyj komendy {prefix}numerki, aby pokazać tą wiadomość.")
    return True, embed


# noinspection SpellCheckingInspection
command_descriptions = {
    "help": "Wyświetla tą wiadomość.",

    "nl": """Mówi jaką mamy następną lekcję.
    Parametry: __godzina__, __minuta__
    Przykład: `{p}nl 9 30` - wyświetliłaby się najbliższa lekcja po godzinie 09:30.
    *Domyślnie pokazana jest najbliższa lekcja od aktualnego czasu*""",

    "nb": """Mówi kiedy jest następna przerwa.
    Parametry: __godzina__, __minuta__
    Przykład: `{p}nb 9 30` - wyświetliłaby się najbliższa przerwa po godzinie 09:30.
    *Domyślnie pokazana jest najbliższa przerwa od aktualnego czasu*""",

    "plan": """Pokazuje plan lekcji dla danego dnia.
    Parametry: __dzień tygodnia__
    Przykłady:
    `{p}plan` - wyświetliłby się plan lekcji na dziś/najbliższy dzień szkolny.
    `{p}plan 2` - wyświetliłby się plan lekcji na wtorek (2. dzień tygodnia).
    `{p}plan pon` - wyświetliłby się plan lekcji na poniedziałek.""",

    "zadanie": """Tworzy nowe zadanie i automatycznie ustawia powiadomienie na dzień przed.
    Natomiast, jeśli w parametrach podane jest hasło 'del' oraz nr zadania, zadanie to zostanie usunięte.
    Parametry: __data__, __grupa__, __treść__ | 'del', __ID zadania__
    Przykłady:
    `{p}zad 31.12.2024 @Grupa 1 Zrób ćwiczenie 5` - stworzyłoby się zadanie na __31.12.2024__\
    dla grupy **pierwszej** z treścią: *Zrób ćwiczenie 5*.
    `{p}zad del 4` - usunęłoby się zadanie z ID: *event-id-4*.""",

    "zadania": "Pokazuje wszystkie zadania domowe, które zostały stworzone za pomocą komendy `{p}zad`.",

    "zad": "Alias komendy `{p}zadanie` lub `{p}zadania`, w zależności od podanych argumentów.",

    "meet": None,

    "cena": """Podaje aktualną cenę dla szukanego przedmiotu na Rynku Społeczności Steam.
    Parametry: __przedmiot__, __waluta__
    Przykłady: 
    `{p}cena Operation Broken Fang Case` - wyświetliłaby się cena dla tego przedmiotu, domyślnie w zł.
    `{p}cena Operation Broken Fang Case waluta=EUR` - wyświetliłaby się cena dla tego przedmiotu w euro.""",

    "sledz": """Zaczyna śledzić dany przedmiot na Rynku Społeczności Steam \
    i wysyła powiadomienie, gdy cena wykroczy podaną granicę.
    Parametry: __nazwa przedmiotu__, __cena minimalna__, __cena maksymalna__,
    Przykład: `{p}sledz Operation Broken Fang Case min=1.00 max=3.00` - stworzyłoby się zlecenie śledzenia tego\
    przedmiotu z powiadomieniem, gdy cena się obniży poniżej 1,00zł lub przekroczy 3,00zł.""",

    "odsledz": """Przestaje śledzić dany przedmiot na Rynku Społeczności Steam.
    Parametry: __nazwa przedmiotu__
    Przykład: `{p}odsledz Operation Broken Fang Case` - zaprzestaje śledzenie ceny tego przedmiotu.""",

    "numerki": "Podaje aktualne szczęśliwe numerki oraz klasy, które są z nich wykluczone.",

    "num": "Alias komendy `{p}numerki`."
}
# noinspection SpellCheckingInspection
command_methods = {
    'help': get_help_message,
    'nl': get_next_lesson,
    'nb': get_next_break,
    'plan': get_lesson_plan,
    'zad': process_homework_events_alias,
    'zadanie': create_homework_event,
    'zadania': get_homework_events,
    'meet': update_meet_link,
    'cena': get_market_price,
    'sledz': start_market_tracking,
    'odsledz': stop_market_tracking,
    'numerki': get_lucky_numbers_embed,
    'num': get_lucky_numbers_embed
}

# noinspection SpellCheckingInspection
automatic_bot_replies = {
    "co jest?": "nie wjem"
}


async def wait_for_zadania_reaction(message: discord.Message, reply_msg: discord.Message) -> None:
    def check_for_valid_reaction(test_reaction, reaction_author):
        return str(test_reaction.emoji) == Emoji.unicode_detective and reaction_author != client.user

    await reply_msg.add_reaction(Emoji.unicode_detective)
    try:
        await client.wait_for('reaction_add', timeout=10.0, check=check_for_valid_reaction)
    except asyncio.TimeoutError:
        # 10 seconds have passed with no user input
        await reply_msg.clear_reactions()
    else:
        # Someone has added detective reaction to message
        await reply_msg.clear_reactions()
        await reply_msg.edit(embed=get_homework_events(message, True)[1])


# This method is called when someone sends a message in the server
@client.event
async def on_message(message: discord.Message) -> None:
    await client.wait_until_ready()
    if client.user in message.mentions:
        message.content = "!help " + message.content
    for reply in automatic_bot_replies:
        if reply.lower().startswith(message.content) and len(message.content) >= 3:
            await message.reply(automatic_bot_replies[reply], mention_author=False)
            return
    author_role_names = [str(role) for role in message.author.roles]
    if message.author == client.user or "Bot" in author_role_names or not message.content.startswith(prefix):
        return
    if not any(group_role in author_role_names for group_role in ["Grupa 1", "Grupa 2"]):
        await message.channel.send(
            f":warning: **Uwaga, {message.author.mention}: nie posiadasz rangi ani do grupy pierwszej "
            f"ani do grupy drugiej.\nUstaw sobie grupę, do której należysz reagując na wiadomość w kanale "
            f"{client.get_channel(773135499627593738).mention} numerem odpowiedniej grupy.**\n"
            f"Możesz sobie tam też ustawić język, na który chodzisz oraz inne rangi.")
    msg_first_word = message.content.lower().lstrip(prefix).split(" ")[0]
    admin_commands = ["exec", "restart", "quit", "exit"]
    if msg_first_word in admin_commands:
        if message.author != client.get_user(member_ids[8 - 1]):
            author_name = message.author.name if message.author.nick is None else message.author.nick
            await message.reply(f"Ha ha! Nice try, {author_name}.")
            return
        if msg_first_word == admin_commands[0]:
            if not message.content.startswith(prefix + "exec "):
                await message.channel.send("Type an expression or command to execute.")
                return
            expression = message.content[len(prefix + "exec "):]
            log_message("Executing code:", expression)
            try:
                if "return " in expression:
                    exec(expression.replace("return ", "locals()['temp'] = "))
                else:
                    try:
                        exec(f"""locals()['temp'] = {expression}""")
                    except SyntaxError:
                        exec(expression)
                exec_result = locals()['temp'] if "temp" in locals() else "Code executed (return value not specified)."
            except Exception as e:
                exec_result = ''.join(traceback.format_exception(type(e), e, e.__traceback__))
            if exec_result is None:
                await message.channel.send("Code executed.")
            else:
                expr = expression.replace("\n", "\n>>> ")
                try:
                    try:
                        result = "```\nDetected JSON content:```json\n" + json.dumps(exec_result, indent=4, ensure_ascii=False)
                    except (TypeError, OverflowError):
                        result = exec_result
                    await message.channel.send(f"Code executed:\n```py\n>>> {expr}\n{result}\n```")
                except discord.errors.HTTPException:
                    await message.channel.send(f"Code executed:\n```py\n>>> {expr}```*Result too long to send in message, attaching file 'result.txt'...*")
                    with open("result.txt", 'w') as file:
                        try:
                            json.dump(exec_result, file, indent=2, ensure_ascii=False)
                        except TypeError:
                            file.write(str(exec_result))
                    await message.channel.send(file=discord.File("result.txt"))
            return

        if msg_first_word == admin_commands[1]:
            await message.channel.send("Restarting bot...")
        else:
            await message.channel.send("Exiting program.")
            file_management.write_log(f"\n    --- Program manually closed by user ('{msg_first_word}' command). ---")
            global restart_on_exit
            restart_on_exit = False
        track_time_changes.stop()
        track_api_updates.stop()
        await client.close()

    if msg_first_word not in command_descriptions:
        return
    # await message.delete()

    log_message(f"Received command: '{message.content}'", "from user:", message.author)
    command_method_to_call_when_executed = command_methods[msg_first_word]
    try:
        reply_is_embed, reply = command_method_to_call_when_executed(message)
    except Exception as e:
        log_message(''.join(traceback.format_exception(type(e), e, e.__traceback__)))
        await message.reply(f"<@{member_ids[8 - 1]}> An exception occurred while executing command `{message.content}`."
                            f" Check the bot logs for details.")
        return
    reply_msg = await message.reply(**{"embed" if reply_is_embed else "content": reply})

    if msg_first_word == "zadania":
        await wait_for_zadania_reaction(message, reply_msg)


def log(*message) -> None:
    """Shorthand for sending a message to the log channel and program output file regardless of log settings."""
    log_message(*message, force=True)


def log_message(*raw_message, force=False) -> None:
    """Determine if the message should actually be logged, and if so, generate the string that should be sent."""
    if not (enable_log_messages or force):
        return
    timestamp = f"{datetime.datetime.now():%Y-%m-%d @ %H:%M:%S}: "
    # Add spaces after each newline so that the actual message is in line to make up for the timestamp at the beginning 
    message = timestamp + ' '.join(map(str, raw_message)).replace("\n", "\n" + " " * len(timestamp))
    file_management.write_log(message)
    log_loop = asyncio.get_event_loop()
    log_loop.create_task(send_log_message(message))


async def send_log_message(message) -> None:
    await client.wait_until_ready()
    await client.get_channel(ChannelID.bot_logs).send(f"```py\n{message}\n```")


def start_bot() -> bool:
    """Log in to the Discord bot and start its functionality.
    This method is blocking -- once the bot is connected, it will run until it's disconnected.

    Returns a boolean that indicates if the bot should be restarted.
    """
    # Save the previous log on startup
    file_management.save_log_file()
    save_on_exit = True
    # Update each imported module before starting the bot.
    # The point of restarting the bot is to update the code without having to manually stop and start the script.
    for module in (file_management, steam_api, web_api, lucky_numbers_api, plan_crawler, substitutions_crawler):
        importlib.reload(module)
    try:
        file_management.read_env_files()
        read_data_file('data.json')
        event_loop = asyncio.get_event_loop()
        try:
            token = os.environ["BOT_TOKEN"]
        except KeyError:
            file_management.write_log("\n    --- CRITICAL ERROR! ---")
            file_management.write_log("'BOT_TOKEN' OS environment variable not found. Program exiting.")
            save_on_exit = False
            # Do not restart bot
            return False
        else:
            # No problems finding OS variable containing bot token. Can login successfully.
            event_loop.run_until_complete(client.login(token))
        # Bot has been logged in, continue with attempt to connect
        try:
            # Blocking call:
            # The program will stay on this line until the bot is disconnected.
            event_loop.run_until_complete(client.connect())
        except KeyboardInterrupt:
            # Raised when the program is forcefully closed (eg. Ctrl+F2 in PyCharm).
            file_management.write_log("\n    --- Program manually closed by user (KeyboardInterrupt exception). ---")
            # Do not restart, since the closure of the bot was specifically requested by the user.
            return False
        else:
            # The bot was exited gracefully (eg. !exit, !restart command issued in Discord)
            file_management.write_log("\n    --- Bot execution terminated successfully. ---")
    finally:
        # Execute this no matter the circumstances, ensures data file is always up-to-date.
        if save_on_exit:
            # The file is saved before the start_bot() method returns any value.
            # Do not send a debug message since the bot is already offline.
            save_data_file(should_log=False)
            file_management.write_log("Successfully saved data file 'data.json'. Program exiting.")
    # By default, when the program is exited gracefully (see above), it is later restarted in 'run.pyw'.
    # If the user issues a command like !exit, !quit, the return_on_exit global variable is set to False,
    # and the bot is not restarted.
    return restart_on_exit


if __name__ == "__main__":
    file_management.write_log("Started bot from main file! Assuming this is debug behaviour.\n")
    use_bot_testing = True
    enable_log_messages = True
    start_bot()
