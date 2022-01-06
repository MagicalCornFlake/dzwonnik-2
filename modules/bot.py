"""Module containing the code relating to the management of the Discord bot client."""

# Standard library imports
import asyncio
import datetime
import json

# Third-party imports
import discord
from discord.ext.tasks import loop

# Local application imports
from . import file_manager, commands, util, ROLE_CODES, MEMBER_IDS, WEEKDAY_NAMES, GROUP_NAMES, Emoji, Weekday
from .commands import help, homework, steam_market, lucky_numbers, substitutions
from .util import web
from .util.api import lucky_numbers as lucky_numbers_api, steam_market as steam_api
from .util.crawlers import lesson_plan as lesson_plan_crawler, substitutions as substitutions_crawler


# These settings ensure that data from the SU ILO API is only fetched a maximum of 45 times a day.
# If the bot finds new data for a given day, it stops checking, so in practice this is usually less than 45.
UPDATE_NUMBERS_AT = 1  # Hours; i.e. check only if it's 01:00 AM
UPDATE_NUMBERS_FOR = 15  # Minutes; i.e. only check from 01:00:00 - 01:14:59
UPDATE_NUMBERS_EVERY = 20  # Seconds; i.e. only check 3 times a minute

# Sets the maximum length of a message that can be sent without causing errors with the Discord API.
MAX_MESSAGE_LENGTH = 4000  # Characters

MY_SERVER_ID: int = 766346477874053130

# The message template to be used when an API call returned an invalid response.
BAD_RESPONSE = "Error! Received an invalid response when performing the web request. Exception trace:\n"

# When somebody sends a message starting with any of the below keys, it replies with the value of that dict pair.
# noinspection SpellCheckingInspection
AUTOMATIC_BOT_REPLIES = {
    MY_SERVER_ID: {
        "co jest?": "nie wjem"
    }
}


class ChannelID:
    """Constant declarations for Discord channnel IDs."""
    RANGI: int = 773135499627593738
    GENERAL: int = 766346477874053132
    NAUKA: int = 769098845598515220
    NUMERKI: int = 928102562710835240
    SUBSTITUTIONS: int = 928101883778854954
    ADMINI: int = 773137866338336768
    BOT_TESTING: int = 832700271057698816
    BOT_LOGS: int = 835561967007432784


class MissingPermissionsException(Exception):
    """Raised when the user does not have the appropriate permissions for performing a command or other action.

    Attributes:
        message -- explanation of the error
    """
    _message = "The user does not have the appropriate permissions to perform that action."

    def __init__(self, message=_message):
        self.message = message
        super().__init__(self.message)


# Initialise the discord client settings
intents = discord.Intents.default()
intents.members = True
client = discord.Client(intents=intents)

# Initialise the object reference to our Discord server
# The value is set once the bot is logged in and ready.
my_server: discord.Guild = None

# Determines the prefix that is to be used before each user command.
prefix: str = '!'

# Makes the log messages sent by the bot more verbose.
enable_log_messages: bool = False

# Determines whether or not the bot should save the data file once it terminates.
restart_on_exit: bool = True

# Used to show the current lesson in the lesson plan (e.g. '!plan' command).
current_period: int = -1

# If this is set, it will override most output channels to be the channel with the given ID.
testing_channel: int = None


def send_log(*raw_message, force: bool = False) -> None:
    """Determine if the message should actually be logged, and if so, generate the string that should be sent."""
    if not (enable_log_messages or force):
        return

    msg = file_manager.log(*raw_message)
    too_long_msg = f"Log message too long ({len(msg)} characters). Check 'bot.log' file."
    msg_to_log = msg if len(msg) <= MAX_MESSAGE_LENGTH else too_long_msg

    log_loop = asyncio.get_event_loop()
    log_loop.create_task(send_log_message(msg_to_log))


async def send_log_message(message) -> None:
    """Send the log message to the `bot_logs` channel."""
    await client.wait_until_ready()
    log_channel: discord.TextChannel = client.get_channel(ChannelID.BOT_LOGS)
    await log_channel.send(f"```py\n{message}\n```")


@client.event
async def on_ready() -> None:
    """Initialise the bot when it comes online."""
    # Enable the circular reference in the 'web' module, since it only works when called from this module.
    web.enable_circular_reference()

    # Report information about logged in guilds
    guilds = {guild.id: guild.name for guild in client.guilds}
    login_message = f"Successfully connected as {client.user}.\nActive guilds:"
    send_log(login_message, guilds, force=True)

    # Initialise server reference
    global my_server
    my_server = client.get_guild(MY_SERVER_ID)  # Konrad's Discord Server

    # Initialise lesson plan forcefully as bot loads; force_update switch bypasses checking for cache
    try:
        result = lesson_plan_crawler.get_lesson_plan(force_update=True)
    except web.InvalidResponseException as e:
        exc = util.format_exception_info(e)
        send_log(f"{BAD_RESPONSE}{exc}", force=True)
    else:
        plan: dict = result[0]
        send_log(f"Initialised lesson plan as {type(plan)}.")
        util.lesson_plan = plan

    # Intialise array of schooldays
    schooldays = [key for key in util.lesson_plan if key in WEEKDAY_NAMES]

    # Initialise set of unique lesson names
    lesson_names = set()
    for schoolday in schooldays:
        for lessons in util.lesson_plan[schoolday]:
            for lesson in lessons:
                lesson_names.add(lesson["name"])

    # Initialise dictionary of lesson links
    for lesson_name in sorted(lesson_names):
        util.lesson_links.setdefault(lesson_name, None)

    # Sets status message on bot start
    status = discord.Activity(
        type=discord.ActivityType.watching, name=get_new_status_msg())
    await client.change_presence(activity=status)

    # Starts loops that run continuously
    main_update_loop.start()

    # Checks if the bot was just restarted
    for channel_id in [ChannelID.BOT_TESTING, ChannelID.BOT_LOGS]:
        channel = client.get_channel(channel_id)
        try:
            last_test_message = await channel.fetch_message(channel.last_message_id)
        except discord.errors.NotFound:
            last_message_404 = f"Could not find last message in channel {channel.name}. It was probably deleted."
            send_log(last_message_404)
        else:
            if last_test_message is None:
                send_log(f"Last message in channel {channel.name} is None.")
            elif last_test_message.author == client.user:
                if last_test_message.content == "Restarting bot...":
                    await last_test_message.edit(content="Restarted bot!")
            else:
                last_message_not_mine = f"Last message in channel {channel.name} was not sent by me."
                send_log(last_message_not_mine)


# This function is called when someone sends a message in the server
@client.event
async def on_message(message: discord.Message) -> None:
    """Handle the commands sent by users."""
    await client.wait_until_ready()
    if client.user in message.mentions:
        message.content = "!help " + message.content
    for reply in AUTOMATIC_BOT_REPLIES.get(message.guild.id, {}):
        if reply.lower().startswith(message.content) and len(message.content) >= 3:
            await message.reply(AUTOMATIC_BOT_REPLIES[reply], mention_author=False)
            return
    author_role_names = [str(role) for role in message.author.roles]
    if message.author == client.user or "Bot" in author_role_names or not message.content.startswith(prefix):
        return
    if not any(group_role in author_role_names for group_role in ["Grupa 1", "Grupa 2"]):
        await message.channel.send(
            f"{Emoji.WARNING} **Uwaga, {message.author.mention}: nie posiadasz rangi ani do grupy pierwszej "
            f"ani do grupy drugiej.\nUstaw sobie grupę, do której należysz reagując na wiadomość w kanale "
            f"{client.get_channel(ChannelID.RANGI).mention} numerem odpowiedniej grupy.**\n"
            f"Możesz sobie tam też ustawić język, na który chodzisz oraz inne rangi.")
    msg_first_word = message.content.lower().lstrip(prefix).split(" ")[0]

    if msg_first_word not in help.INFO:
        return

    received_command_msg = f"Received command '{message.content}' from {message.author}"
    send_log(received_command_msg, force=True)
    command_info = help.INFO[msg_first_word]
    callback_function = command_info["function"]
    try:
        reply_is_embed, reply = callback_function(message)
    except MissingPermissionsException as e:
        error_message = f"{Emoji.WARNING} Nie posiadasz uprawnień do {e}."
        message.reply(error_message)
    except Exception as e:
        await ping_konrad()
        send_log(util.format_exception_info(e), force=True)
        await message.reply(f":x: Nastąpił błąd przy wykonaniu tej komendy. Administrator bota (Konrad) został o tym powiadomiony.")
    else:
        reply_msg = await try_send_message(message, True, {"embed" if reply_is_embed else "content": reply}, reply)
        on_success_coroutine = command_info.get("on_completion")
        if on_success_coroutine:
            await on_success_coroutine(message, reply_msg)


def get_new_status_msg(query_time: datetime.datetime = None) -> str:
    """Determine the current lesson status message.

    Arguments:
        query_time -- the time to get the status for.
    """
    global current_period
    # Default time to check is current time
    query_time = query_time or datetime.datetime.now()
    send_log(f"Updating bot status ...", force=True)
    result = commands.get_next_period(query_time)
    next_period_is_today, next_period, next_lesson_weekday = result

    if next_period_is_today:
        # Get the period of the next lesson
        roles = list(ROLE_CODES.keys())[1:]
        params = next_period % 10, next_lesson_weekday, roles
        lesson = commands.get_lesson_by_roles(*params)
        if lesson:
            current_period = lesson['period']
            send_log("The next lesson is on period", lesson['period'])
        # Get the period of the first lesson
        for first_period, lessons in enumerate(util.lesson_plan[WEEKDAY_NAMES[query_time.weekday()]]):
            if lessons:
                send_log("The first lesson is on period", first_period)
                break

        if next_period < 10:
            # Currently break time
            time = util.get_formatted_period_time(current_period).split('-')[0]
            if current_period == first_period:
                # Currently before school
                current_period = -1
                new_status_msg = "szkoła o " + time
            else:
                new_status_msg = "przerwa do " + time
        else:
            # Currently lesson
            # Dictionary with lesson group code and lesson name
            msgs: dict[str, str] = {}
            for role_code in list(ROLE_CODES.keys())[1:]:
                params = current_period, next_lesson_weekday, [role_code]
                lesson = commands.get_lesson_by_roles(*params)
                if not lesson or lesson["period"] > current_period:
                    # No lesson for that group
                    skipping_lesson_msg = f"Skipping lesson: {lesson} on period {current_period}."
                    send_log(skipping_lesson_msg)
                    continue
                send_log("Validated lesson:", lesson)
                msgs[lesson['group']] = util.get_lesson_name(lesson['name'])
                # Found lesson for 'grupa_0' (whole class)
                if lesson['group'] == "grupa_0":
                    found_lesson_msg = "Found lesson for entire class, skipping checking individual groups."
                    send_log(found_lesson_msg)
                    break
            # set(msgs.values()) returns a list of unique lesson names
            lesson_text = "/".join(set(msgs.values()))
            if len(msgs) == 1 and list(msgs.keys())[0] != "grupa_0":
                # Specify the group the current lesson is for if only one group has it
                lesson_text += " " + GROUP_NAMES[list(msgs.keys())[0]]
            new_status_msg = f"{lesson_text} do {util.get_formatted_period_time(current_period).split('-')[1]}"
    else:
        # After the last lesson for the given day
        current_period = -1
        is_weekend = query_time.weekday() >= Weekday.FRIDAY
        new_status_msg = "weekend!" if is_weekend else "koniec lekcji!"
    send_log(f"... new status message is '{new_status_msg}'.", force=True)
    send_log(f"Current period: {current_period}", force=True)
    return new_status_msg


async def remind_about_homework_event(event: homework.HomeworkEvent, tense: str) -> None:
    """Send a message reminding about the homework event."""
    mention_text = "@everyone"  # To be used at the beginning of the reminder message
    event_name = event.title
    for role in ROLE_CODES:
        if role == event.group:
            mention_role = discord.utils.get(
                my_server.roles, name=ROLE_CODES[role])
            if role != "grupa_0":
                mention_text = my_server.get_role(mention_role.id).mention
            break
    chnl: int = testing_channel or ChannelID.NAUKA
    target_channel: discord.TextChannel = client.get_channel(chnl)
    # Which tense to use in the reminder message
    when = {
        "today": "dziś jest",
        "tomorrow": "jutro jest",
        "past": f"{event.deadline} było",
        # 'future' is not really needed but I added it cause why not
        "future": f"{event.deadline} jest"
    }[tense]  # tense can have a value of 'today', 'tomorrow' or 'past'
    message: discord.Message = await target_channel.send(f"{mention_text} Na {when} zadanie: **{event_name}**.")
    emojis = [Emoji.UNICODE_CHECK, Emoji.UNICODE_ALARM_CLOCK]
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
            await message.edit(content=f"{Emoji.CHECK_2} Zaznaczono zadanie `{event_name}` jako odrobione.")
        else:  # Reaction emoji is :alarm_clock:
            await snooze_event()
    await message.clear_reactions()
    # Updates data.json so that if the bot is restarted the event's parameters are saved
    file_manager.save_data_file()


@loop(seconds=1)
async def main_update_loop() -> None:
    """Routinely fetches data from various APIs to ensure the cache is up-to-date, and also regularly performs non-resource-intensive tasks that do not connect to APIs.

    API updates:
        - Steam Community Market item prices -- every 30 min
        - The substitutions from the I LO website -- every 1 h
        - The lucky numbers from the SUI LO API -- according to the settings

    Non-API updates:
        - The bot status -- every 1 min
        - Homework event deadlines-- every 1 min
    """

    current_time = datetime.datetime.now()  # Today's time
    await check_for_due_homework(current_time)

    # Tasks that only update on the first second of a given minute
    if current_time.second == 0:
        # Update the bot status once a minute
        await check_for_status_updates(current_time)

        if current_time % 30 == 0:
            # Update the Steam Market prices every half hour
            await check_for_steam_market_updates()

            if current_time.minute == 0:
                # Update the substitutions cache every hour
                await check_for_substitutions_updates()

    # Check if the lucky numbers data is outdated
    try:
        # Try to parse the lucky numbers data date
        cached_date: datetime.datetime = lucky_numbers_api.cached_data["date"]
    except (KeyError, AttributeError) as e:
        # Lucky numbers data does not contain a date
        await ping_konrad()
        send_log(util.format_exception_info(e), force=True)
    else:
        # Lucky numbers data contains a valid date

        if cached_date == current_time.date() or current_time.hour != UPDATE_NUMBERS_AT:
            # Data does not need to be updated; only update at the given time
            return
         # The bot will update every x seconds so that it doesn't exceed the max
        if current_time.minute < UPDATE_NUMBERS_FOR or current_time.second % UPDATE_NUMBERS_EVERY:
            # Initial update period of API update window; don't update more than the maximum
            return
        # Lucky numbers data is not current; update it
        await check_for_lucky_numbers_updates()


async def check_for_status_updates(current_time: datetime.datetime) -> None:
    """Checks if the current hour and minute is in any time slot for the lesson plan timetable."""
    if any([current_time.hour, current_time.minute] in times for times in util.lesson_plan["Godz"]):
        # Check is successful, bot updates Discord status
        msg: str = get_new_status_msg()
        status = discord.Activity(type=discord.ActivityType.watching, name=msg)
        await client.change_presence(activity=status)


async def check_for_due_homework(current_time: datetime.datetime) -> None:
    """Checks if the bot should make a reminder about due homework."""
    tomorrow = current_time.date() + datetime.timedelta(days=1)  # Today's date + 1 day
    for event in homework.homework_events:
        reminder_time = datetime.datetime.strptime(
            event.reminder_date, "%d.%m.%Y %H")
        event_time = datetime.datetime.strptime(event.deadline, "%d.%m.%Y")
        if not event.reminder_is_active or reminder_time > current_time:
            # This piece of homework has already had a reminder issued; ignore it
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


@main_update_loop.before_loop
async def wait_before_starting_loop() -> None:
    await client.wait_until_ready()


async def check_for_steam_market_updates() -> None:
    """Checks if any tracked item's price has exceeded the established boundaries."""
    for item in steam_market.tracked_market_items:
        await asyncio.sleep(3)
        try:
            result = steam_api.get_item(item.name)
            price = steam_api.get_item_price(result)
        except Exception as http_exc:
            await ping_konrad()
            send_log(web.get_error_message(http_exc), force=True)
            return
        # Strips the price string of any non-digit characters and returns it as an integer
        char_list = [char if char in "0123456789" else '' for char in price]
        price = int(''.join(char_list))
        if item.min_price < price < item.max_price:
            continue
        target_channel = client.get_channel(
            testing_channel or ChannelID.ADMINI)
        await target_channel.send(f"{Emoji.CASH} Uwaga, <@{item.author_id}>! "
                                  f"Przedmiot *{item.name}* kosztuje teraz **{price/100:.2f}zł**.")
        steam_market.tracked_market_items.remove(item)
        file_manager.save_data_file()


async def check_for_lucky_numbers_updates() -> None:
    """Updates the lucky numbers cache and announces announces the new numbers in the specified channel if it has changed."""
    try:
        old_cache = lucky_numbers_api.update_cache()
    except web.InvalidResponseException as e:
        await ping_konrad()
        exc: str = util.format_exception_info(e)
        send_log(f"Lucky numbers update: {BAD_RESPONSE}{exc}", force=True)
    else:
        if old_cache != lucky_numbers_api.cached_data:
            send_log(f"Lucky numbers data updated!", force=True)
            new_str = lucky_numbers_api.serialise(pretty=True)
            old_str = lucky_numbers_api.serialise(old_cache, pretty=True)
            send_log(f"New data: {new_str}\nOld data: {old_str}", force=True)
            target_channel = client.get_channel(
                testing_channel or ChannelID.NUMERKI)
            await target_channel.send(embed=lucky_numbers.get_lucky_numbers_embed()[1])
            file_manager.save_data_file()


async def check_for_substitutions_updates() -> None:
    """Updates the substitutions cache and announces the new data in the specified channel if it has changed."""
    try:
        old_cache = file_manager.cache_exists("subs")
        result = substitutions_crawler.get_substitutions(True)
        new_cache, cache_existed = result
        if "error" in new_cache:
            raise RuntimeError("Substitutions data could not be parsed.")
    except web.InvalidResponseException as e:
        # The web request returned an invalid response; log the error details
        if e.status_code == 403:
            send_log("Suppressing 403 Forbidden on substitutions page.", force=True)
            return
        exc: str = util.format_exception_info(e)
        exception_message = f"Substitutions update: {BAD_RESPONSE}{exc}"
    except RuntimeError as err_desc:
        # The HTML parser returned an error; log the error details
        exc: str = new_cache.get("error")
        exception_message = f"Error! {err_desc} Exception trace:\n{exc}"
    else:
        if cache_existed:
            # The cache was not updated. Do nothing.
            return
        send_log("Substitution data updated!", force=True)
        # Announce the new substitutions
        target_channel = client.get_channel(
            testing_channel or ChannelID.SUBSTITUTIONS)
        await target_channel.send(embed=substitutions.get_substitutions_embed()[1])
        return
    # If the check wasn't completed successfully, ping @Konrad and log the error details.
    await ping_konrad()
    send_log(exception_message, force=True)


async def set_offline_status() -> None:
    """Sets the bot's Discord status to 'offline'."""
    await client.change_presence(status=discord.Status.offline)


async def ping_konrad(channel_id: int = ChannelID.BOT_LOGS) -> None:
    """Sends a message to the specified channel mentioning MagicalCornFlake#0520.

    Arguments:
        channel_id -- the ID of the channel to send the message to. By default, this is the ID of the `bot_logs` channel.
    """
    await client.get_channel(channel_id).send(f"<@{MEMBER_IDS[8 - 1]}>")


async def try_send_message(user_message: discord.Message, should_reply: bool, send_args: dict, on_fail_data, on_fail_msg: str = None) -> discord.message:
    send_method = user_message.reply if should_reply else user_message.channel.send
    try:
        reply_msg = await send_method(**send_args)
    except discord.errors.HTTPException:
        send_log("Message too long. Length of data:", len(str(on_fail_data)))
        reply_msg = await send_method(on_fail_msg or "Komenda została wykonana pomyślnie, natomiast odpowiedź jest zbyt długa. Załączam ją jako plik tekstowy.")
        should_iterate = on_fail_msg and type(on_fail_data) is list
        if type(on_fail_data) is discord.Embed:
            on_fail_data = {"embed": on_fail_data.to_dict()}
        with open("result.txt", 'w') as file:
            results: list[str] = []
            for element in on_fail_data if should_iterate else [on_fail_data]:
                processing_element_msg = f"Processing element with type {type(element)}"
                send_log(processing_element_msg, force=True)
                if type(element) in [list, dict, tuple]:
                    try:
                        tmp = json.dumps(element, indent=2, ensure_ascii=False)
                    except TypeError:
                        send_log("Could not parse element as JSON.", force=True)
                    else:
                        results.append(tmp)
                        continue
                if type(element) is bytes:
                    results.append(element.decode('UTF-8'))
                else:
                    results.append(str(element))
            file.write("\n".join(results))
        await user_message.channel.send(file=discord.File("result.txt"))
    return reply_msg
