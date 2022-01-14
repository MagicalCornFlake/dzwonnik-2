"""Module containing the code relating to the management of the Discord bot client."""

# Standard library imports
import asyncio
import datetime
import json

# Third-party imports
import discord
from discord.ext.tasks import loop

# Local application imports
from . import file_manager, commands, util
from . import Emoji, Weekday, ROLE_CODES, MEMBER_IDS, WEEKDAY_NAMES, GROUP_NAMES
from .commands import get_help, homework, steam_market, lucky_numbers, substitutions
from .util import web
from .util.api import lucky_numbers as lucky_numbers_api, steam_market as steam_api
from .util.crawlers import lesson_plan as lesson_plan_api, substitutions as substitutions_api


# These settings ensure that data from the SU ILO API is only fetched a maximum of 45 times a day.
# If the bot finds new data for a given day, it stops checking, so usually less than 45.
UPDATE_NUMBERS_AT = 1  # Hours; i.e. check only if it's 01:00 AM
UPDATE_NUMBERS_FOR = 15  # Minutes; i.e. only check from 01:00:00 - 01:14:59
UPDATE_NUMBERS_EVERY = 20  # Seconds; i.e. only check 3 times a minute

# Sets the maximum length of a message that can be sent without causing errors with the Discord API.
MAX_MESSAGE_LENGTH = 4000  # Characters

MY_SERVER_ID: int = 766346477874053130

# The message template to be used when an API call returned an invalid response.
BAD_RESPONSE = "Error! Received an invalid response from web request. Exception trace:\n"
# The template for the log message sent when the bot's status is updated
STATUS_LOG_TEMPLATE = "... new status message: '{}'.\n... current period: {}\n... next period: {}"

RESTARTED_BOT_MSG = "Restarted bot!"

HOMEWORK_EMOJI = Emoji.UNICODE_CHECK, Emoji.UNICODE_ALARM_CLOCK

# If a message starts with any of the below keys, the bot will reply appropriately.
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
    """Raised when the user does not have the appropriate permissions.
    Can be used when the user is attempting to use a command or perform another restricted action.

    Attributes:
        message -- explanation of the error
    """
    _message = "The user does not have the appropriate permissions to perform that action."

    def __init__(self, message=_message):
        self.message = message
        super().__init__(self.message)


# Initialise the discord client intent settings
desired_intents = ["guilds", "members", "messages", "reactions", "typing"]
intents = discord.Intents(**{intent: True for intent in desired_intents})
client = discord.Client(intents=intents)

# Determines the prefix that is to be used before each user command.
prefix: str = '!'

# Makes the log messages sent by the bot more verbose.
verbose_log_messages: bool = False

# Determines whether or not the bot should save the data file once it terminates.
restart_on_exit: bool = True

# If this is set, it will override most output channels to be the channel with the given ID.
testing_channel: int = None


def send_log(*raw_message, force: bool = False) -> None:
    """Determine if the message should actually be logged.
    If it should, generate the string that should be sent.
    """
    if not (verbose_log_messages or force):
        return

    msg = file_manager.log(*raw_message)
    too_long_msg = f"Log message too long ({len(msg)} characters). Check 'bot.log' file."
    msg_to_log = msg if len(msg) <= MAX_MESSAGE_LENGTH else too_long_msg

    log_loop = asyncio.get_event_loop()
    log_loop.create_task(send_log_message(msg_to_log))


async def send_log_message(message) -> None:
    """Send the log message to the `bot_logs` channel."""
    try:
        await client.wait_until_ready()
        log_chnl: discord.TextChannel = client.get_channel(ChannelID.BOT_LOGS)
        await log_chnl.send(f"```py\n{message}\n```")
    except (RuntimeError, OSError) as exception:
        could_not_log_msg = f"Could not log message: '{message}'. Exception: {exception}"
        file_manager.log(could_not_log_msg)


@client.event
async def on_ready() -> None:
    """Initialise the bot when it comes online."""

    # Redefine the 'web' module's internal 'send_log' function to enable Discord channel logging.
    web.send_log = send_log

    # Report information about logged in guilds
    guilds = {guild.id: guild.name for guild in client.guilds}
    login_message = f"Successfully connected as {client.user}.\nActive guilds:"
    send_log(login_message, guilds, force=True)

    # Initialise lesson plan forcefully; force_update switch bypasses checking for cache.
    try:
        result = lesson_plan_api.get_lesson_plan(force_update=True)
    except web.InvalidResponseException as web_exc:
        exc = util.format_exception_info(web_exc)
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

    # Starts loops that run continuously
    main_update_loop.start()


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
    if message.author == client.user or "Bot" in author_role_names:
        return
    if not message.content.startswith(prefix):
        return
    if not any(group_role in author_role_names for group_role in ["Grupa 1", "Grupa 2"]):
        await message.channel.send(
            f"{Emoji.WARNING} **Uwaga, {message.author.mention}: nie posiadasz rangi ani do grupy "
            f"pierwszej ani do grupy drugiej.\nUstaw sobie grupę, do której należysz reagując na "
            f"wiadomość w kanale {client.get_channel(ChannelID.RANGI).mention} numerem "
            f"odpowiedniej grupy.**\n"
            f"Możesz sobie tam też ustawić język, na który chodzisz oraz inne rangi.")
    msg_first_word = message.content.lower().lstrip(prefix).split(" ")[0]

    if msg_first_word not in get_help.INFO:
        return

    received_command_msg = f"Received command '{message.content}' from {message.author}"
    send_log(received_command_msg, force=True)
    command_info = get_help.INFO[msg_first_word]
    callback_function = command_info["function"]
    async with message.channel.typing():
        try:
            reply_is_embed, reply = callback_function(message)
        except MissingPermissionsException as invalid_perms_exc:
            error_message = f"{Emoji.WARNING} Nie posiadasz uprawnień do {invalid_perms_exc}."
            message.reply(error_message)
        except Exception as invalid_perms_exc:  # pylint: disable=broad-except
            await ping_konrad()
            send_log(util.format_exception_info(invalid_perms_exc), force=True)
            await message.reply(":x: Nastąpił błąd przy wykonaniu tej komendy. "
                                "Administrator bota (Konrad) został o tym powiadomiony.")
        else:
            args = {"embed" if reply_is_embed else "content": reply}
            reply_msg = await try_send_message(message, True, args, reply)
            on_success_coroutine = command_info.get("on_completion")
            if on_success_coroutine:
                await on_success_coroutine(message, reply_msg)


def get_new_status_msg(query_time: datetime.datetime = None) -> str or False:
    """Determine the current lesson status message.

    Arguments:
        query_time -- the time to get the status for.

    Returns the new status as a string, or False indicating that the status does not need updating.
    """
    # Default time to check is current time
    query_time = query_time or datetime.datetime.now()
    send_log("Updating bot status ...", force=True)
    # Get the period of the end of the current lesson (if any) or the beginning of the next break.
    result = commands.get_next_period(query_time)
    next_period_is_today, current_period, next_lesson_weekday = result

    if next_period_is_today:
        util.current_period = current_period % 10
        # Get the details of the next lesson.
        params = [util.current_period, next_lesson_weekday, ROLE_CODES.keys()]
        lesson = commands.get_lesson_by_roles(*params)
        if lesson:
            util.next_period = lesson['period']
            send_log(f"The next lesson is on period {util.next_period}.")
        # Get the period of the first lesson
        first_period = -1  # Initialise period so that PyLint does not complain
        weekday_name = WEEKDAY_NAMES[query_time.weekday()]
        plan_for_given_day: list[list] = util.lesson_plan[weekday_name]
        for first_period, lessons in enumerate(plan_for_given_day):
            if lessons:
                send_log(f"The first lesson is on period {first_period}.")
                break

        if current_period < 10 or util.next_period != util.current_period:
            # Currently break time
            formatted_time = util.get_formatted_period_time(util.next_period)
            time = formatted_time.split('-', maxsplit=1)[0]
            if util.next_period == first_period:
                # Currently before school
                util.current_period = -1
                send_log("The current period is before school starts (-1).")
                new_status_msg = "szkoła o " + time
            else:
                send_log(f"It is currently period {util.current_period}.")
                new_status_msg = "przerwa do " + time
        else:
            # Currently lesson
            # Dictionary with lesson group code and lesson name
            msgs: dict[str, str] = {}
            for role_code in list(ROLE_CODES.keys())[1:]:
                params[-1] = ["grupa_0", role_code]
                lesson = commands.get_lesson_by_roles(*params)
                if not lesson or lesson["period"] > util.next_period:
                    # No lesson for that group
                    continue
                send_log("... validated!", lesson)
                msgs[lesson['group']] = util.get_lesson_name(lesson['name'])
                # Found lesson for 'grupa_0' (whole class)
                if lesson['group'] == "grupa_0":
                    found_lesson_msg = "Found lesson for entire class, skipping individual groups."
                    send_log(found_lesson_msg)
                    break
            # set(msgs.values()) returns a list of unique lesson names
            lesson_text = "/".join(set(msgs.values()))
            if len(msgs) == 1 and list(msgs.keys())[0] != "grupa_0":
                # Specify the group the current lesson is for if only one group has it
                lesson_text += " " + GROUP_NAMES[list(msgs.keys())[0]]
            formatted_time = util.get_formatted_period_time()
            new_status_msg = f"{lesson_text} do {formatted_time.split('-')[1]}"
    else:
        # After the last lesson for the given day
        util.current_period = -1
        is_weekend = query_time.weekday() >= Weekday.FRIDAY
        new_status_msg = "weekend!" if is_weekend else "koniec lekcji!"
    if client.activity and new_status_msg == client.activity.name:
        send_log("... new status message is unchanged.", force=True)
        return False
    fmt_vars = new_status_msg, util.current_period, util.next_period
    status_log_msg = STATUS_LOG_TEMPLATE.format(*fmt_vars)
    send_log(status_log_msg, force=True)
    return new_status_msg


def validate_reaction(test_reaction: discord.Reaction, reaction_user: discord.Member) -> bool:
    """Checks whether or not the reaction contains the correct emoji."""
    emoji_valid = str(test_reaction.emoji) in HOMEWORK_EMOJI
    return reaction_user != client.user and emoji_valid


async def remind_about_homework_event(event: homework.HomeworkEvent, tense: str) -> None:
    """Send a message reminding about the homework event."""

    # Initialise server reference
    my_server: discord.Guild = client.get_guild(
        MY_SERVER_ID)  # Konrad's Discord Server

    mention_text = "@everyone"  # To be used at the beginning of the reminder message
    event_name = event.title
    for role, name in ROLE_CODES.items():
        if role == event.group:
            mention_role = discord.utils.get(my_server.roles, name=name)
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
    reminder_message = f"{mention_text} Na {when} zadanie: **{event_name}**."
    message: discord.Message = await target_channel.send(reminder_message)
    for emoji in HOMEWORK_EMOJI:
        await message.add_reaction(emoji)

    async def snooze_event() -> None:
        """Increases the event's due date by one hour."""
        new_reminder_time = datetime.datetime.now() + datetime.timedelta(hours=1)
        event.reminder_date = new_reminder_time.strftime("%d.%m.%Y %H")
        snoozed_message = (f":alarm_clock: Przełożono powiadomienie dla zadania `{event_name}`"
                           f" na {str(new_reminder_time.hour).zfill(2)}:00.")
        await message.edit(content=snoozed_message)

    try:
        reaction, _ = await client.wait_for('reaction_add', timeout=120.0, check=validate_reaction)
    except asyncio.TimeoutError:  # 120 seconds have passed with no user input
        await snooze_event()
    else:
        if str(reaction.emoji) == HOMEWORK_EMOJI[0]:
            # Reaction emoji is ':ballot_box_with_check:'
            event.reminder_is_active = False
            completed_msg = f"{Emoji.CHECK_2} Zaznaczono zadanie `{event_name}` jako odrobione."
            await message.edit(content=completed_msg)
        else:  # Reaction emoji is :alarm_clock:
            await snooze_event()
    await message.clear_reactions()
    # Updates data.json so that if the bot is restarted the event's parameters are saved
    file_manager.save_data_file()


@loop(seconds=1)
async def main_update_loop() -> None:
    """Routinely fetches data from various APIs to ensure the cache is up-to-date.
    And also regularly performs non-resource-intensive tasks that do not connect to APIs.

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

        if current_time.minute % 30 == 0:
            # Update the Steam Market prices every half hour
            await check_for_steam_market_updates()

            if current_time.minute == 0:
                # Update the substitutions cache every hour
                await check_for_substitutions_updates()

    # Check if the lucky numbers data is outdated
    try:
        # Try to parse the lucky numbers data date
        cached_date: datetime.datetime = lucky_numbers_api.cached_data["date"]
    except (TypeError, KeyError) as exception:
        # Lucky numbers data does not contain a date
        await ping_konrad()
        fmt_exc = util.format_exception_info(exception)
        send_log(fmt_exc, force=True)
    else:
        if cached_date == current_time.date() or current_time.hour != UPDATE_NUMBERS_AT:
            # Data does not need to be updated; only update at the given time
            return
            # The bot will update every x seconds so that it doesn't exceed the max
        if current_time.minute >= UPDATE_NUMBERS_FOR or current_time.second % UPDATE_NUMBERS_EVERY:
            # Initial update period of API update window; don't update more than the maximum
            return
    # Lucky numbers data is not current; update it
    await check_for_lucky_numbers_updates()


async def check_for_status_updates(current_time: datetime.datetime, force: bool = False) -> None:
    """Checks if the current hour and minute is in any time slot for the lesson plan timetable."""
    now = current_time.hour, current_time.minute
    # Loop throught each period to see if the current time is the same as either start or end time
    if not force:
        for start_end_times in util.lesson_plan["Godz"]:
            if now in start_end_times:
                # Current time is either the period's start or end time; stop checking further times
                break
        else:
            # We have reached the end of the loop without finding a match
            return
    # Check is successful; update bot's Discord status
    msg: str = get_new_status_msg()
    if not msg:
        # Do not update the status if it evaluates to False (i.e. status does not need updating)
        return
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
    """Wait for the client to initialise before starting loops."""
    await client.wait_until_ready()
    await check_for_status_updates(datetime.datetime.now(), force=True)

    # If there was a message sent the last time the bot closed, edit or reply to it.
    msg_info = file_manager.on_exit_msg
    try:
        last_msg_chnl: discord.TextChannel = await client.fetch_channel(msg_info["channel_id"])
        last_msg: discord.Message = await last_msg_chnl.fetch_message(msg_info["message_id"])
        if msg_info["is_restart"]:
            await last_msg.edit(content=RESTARTED_BOT_MSG)
        else:
            await last_msg.reply(RESTARTED_BOT_MSG)
    except KeyError:
        # The keys do not exist in the on exit message data
        pass
    # Reset the on exit message so that it is not replied to twice.
    file_manager.on_exit_msg = {}


async def check_for_steam_market_updates() -> None:
    """Checks if any tracked item's price has exceeded the established boundaries."""
    for item in steam_market.tracked_market_items:
        await asyncio.sleep(3)
        try:
            result = steam_api.get_item(item.name)
            price = steam_api.get_item_price(result)
        except web.WebException as web_exc:
            await ping_konrad()
            send_log(web.get_error_message(web_exc), force=True)
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
    """Updates the lucky numbers cache.

    If it has changed, announces announces the new numbers in the specified channel.
    """
    try:
        old_cache = lucky_numbers_api.update_cache()
    except web.InvalidResponseException as web_exc:
        await ping_konrad()
        exc: str = util.format_exception_info(web_exc)
        send_log(f"Lucky numbers update: {BAD_RESPONSE}{exc}", force=True)
    else:
        if old_cache != lucky_numbers_api.cached_data:
            old_str: str = lucky_numbers_api.serialise(old_cache, pretty=True)
            send_log(
                f"Lucky numbers data updated! Old data:\n{old_str}", force=True)
            target_channel = client.get_channel(
                testing_channel or ChannelID.NUMERKI)
            await target_channel.send(embed=lucky_numbers.get_lucky_numbers_embed()[1])
            file_manager.save_data_file()


async def check_for_substitutions_updates() -> None:
    """Updates the substitutions cache.

    If it has changed, announces the new data in the specified channel.
    """
    try:
        # old_cache = file_manager.cache_exists("subs")
        new_cache, cache_existed = substitutions_api.get_substitutions(True)
        if "error" in new_cache:
            raise RuntimeError("Substitutions data could not be parsed.")
    except web.InvalidResponseException as web_exc:
        # The web request returned an invalid response; log the error details
        if web_exc.status_code == 403:
            send_log("Suppressing 403 Forbidden on substitutions page.", force=True)
            return
        exc: str = util.format_exception_info(web_exc)
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
        success, subs_msg = substitutions.get_substitutions_embed()
        if success:
            await target_channel.send(embed=subs_msg)
            return
        exception_message = subs_msg
    # If the check wasn't completed successfully, ping @Konrad and log the error details.
    await ping_konrad()
    send_log(exception_message, force=True)


async def close() -> None:
    """Sets the bot's Discord status to 'offline' and terminates it."""
    await client.wait_until_ready()
    await client.change_presence(status=discord.Status.offline)
    # Sleep for 500 ms to ensure that the client.close() coroutine is the last to execute.
    await asyncio.sleep(0.5)
    await client.close()


async def ping_konrad(channel_id: int = ChannelID.BOT_LOGS) -> None:
    """Sends a message to the specified channel mentioning MagicalCornFlake#0520.

    Arguments:
        channel_id -- the ID of the channel to send the message to. By default,
        this is the ID of the `bot_logs` channel.
    """
    await client.get_channel(channel_id).send(f"<@{MEMBER_IDS[8 - 1]}>")


async def try_send_message(user_message: discord.Message, should_reply: bool, send_args: dict,
                           on_fail_data, on_fail_msg: str = None) -> discord.Message:
    """Attempts to send a message. If it's too long, sends a text file with the contents instead.

    Arguments:
        user_message -- the user message reference to reply to, if necessary.
        should_reply -- a boolean indicating if the message should be a reply to the user message.
        send_args -- a dictionary containing either the key 'content' or 'embed'.
        on_fail_data -- the data to send in the text file if sending fails.
    """
    default_fail_msg = ("Komenda została wykonana pomyślnie, natomiast odpowiedź jest zbyt długa."
                        " Załączam ją jako plik tekstowy.")
    send_method = user_message.reply if should_reply else user_message.channel.send
    try:
        reply_msg = await send_method(**send_args)
    except discord.errors.HTTPException:
        send_log("Message too long. Length of data:", len(str(on_fail_data)))
        reply_msg = await send_method(on_fail_msg or default_fail_msg)
        should_iterate = on_fail_msg and isinstance(on_fail_data, list)
        if isinstance(on_fail_data, discord.Embed):
            on_fail_data = {"embed": on_fail_data.to_dict()}
        with open("result.txt", 'w', encoding="UTF-8") as file:
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
                if isinstance(element, bytes):
                    results.append(element.decode('UTF-8'))
                else:
                    results.append(str(element))
            file.write("\n".join(results))
        await user_message.channel.send(file=discord.File("result.txt"))
    return reply_msg
