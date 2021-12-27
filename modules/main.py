"""Dzwonnik 2, a Discord bot, by Konrad Guzek."""

# Standard library imports
import asyncio
import datetime
import importlib
import json
import os

# Third-party imports
import discord
from discord.ext.tasks import loop

# Local application imports
from . import file_manager, commands, util, my_server_id, role_codes, prefix, member_ids, weekday_names, group_names, ChannelID, Emoji, Weekday
from .commands import help, homework, steam_market
from .util.api import steam_api, lucky_numbers_api
from .util.crawlers import plan_crawler, substitutions_crawler


my_server = util.client.get_guild(my_server_id)  # Konrad's Discord Server

# This method is called when the bot comes online
@util.client.event
async def on_ready() -> None:
    # Report information about logged in guilds
    guilds = {guild.id: guild.name for guild in util.client.guilds}
    util.send_log(f"Successfully logged in as {util.client.user}\nActive guilds:", guilds, force=True)
    
    # Initialise server reference
    global my_server
    my_server = util.client.get_guild(my_server_id)

    # Initialise lesson plan forcefully as bot loads; force_update switch bypasses checking for cache
    util.lesson_plan = plan_crawler.get_lesson_plan(force_update=True)[0]

    # Sets status message on bot start
    status = discord.Activity(type=discord.ActivityType.watching, name=get_new_status_msg())
    await util.client.change_presence(activity=status)

    # Starts loops that run continuously
    track_time_changes.start()
    track_api_updates.start()

    # Checks if the bot was just restarted
    for channel_id in [ChannelID.bot_testing, ChannelID.bot_logs]:
        channel = util.client.get_channel(channel_id)
        try:
            last_test_message = await channel.fetch_message(channel.last_message_id)
        except discord.errors.NotFound:
            util.send_log(f"Could not find last message in channel {channel.name}. It was probably deleted.")
        else:
            if last_test_message is None:
                util.send_log(f"Last message in channel {channel.name} is None.")
            elif last_test_message.author == util.client.user:
                if last_test_message.content == "Restarting bot...":
                    await last_test_message.edit(content="Restarted bot!")
            else:
                util.send_log(f"Last message in channel {channel.name} was not sent by me.")


use_bot_testing = False
restart_on_exit = True


def get_new_status_msg(query_time: datetime.datetime = None) -> str:
    """Determine the current lesson status message.
    
    Arguments:
        query_time -- the time to get the status for.
    """
    # Default time to check is current time
    query_time = query_time or datetime.datetime.now()
    util.send_log(f"Updating bot status ...")
    next_period_is_today, next_period, next_lesson_weekday = commands.get_next_period(query_time)
    if next_period_is_today:
        # Get the period of the next lesson
        lesson = commands.get_lesson_by_roles(next_period % 10, next_lesson_weekday, list(role_codes.keys())[1:])
        if lesson:
            current_period = lesson['period']
            util.send_log("The next lesson is on period", lesson['period'])
        # Get the period of the first lesson
        for first_period, lessons in enumerate(util.lesson_plan[weekday_names[query_time.weekday()]]):
            if lessons:
                util.send_log("The first lesson is on period", first_period)
                break

        if next_period < 10:
            # Currently break time
            if current_period == first_period:
                # Currently before school
                new_status_msg = "szkoła o " + util.get_formatted_period_time(first_period).split('-')[0]
            else:
                new_status_msg = "przerwa do " + util.get_formatted_period_time(current_period).split('-')[0]
        else:
            # Currently lesson
            msgs: dict[str, str] = {}  # Dictionary with lesson group code and lesson name
            for role_code in list(role_codes.keys())[1:]:
                lesson = commands.get_lesson_by_roles(current_period, next_lesson_weekday, [role_code])
                if not lesson or lesson["period"] > current_period:
                    # No lesson for that group
                    util.send_log("Skipping lesson:", lesson, "on period", current_period)
                    continue
                util.send_log("Validated lesson:", lesson)
                msgs[lesson['group']] = commands.get_lesson_name(lesson['name'])
                # Found lesson for 'grupa_0' (whole class)
                if lesson['group'] == "grupa_0":
                    util.send_log("Found lesson for entire class, skipping checking individual groups.")
                    break
            # set(msgs.values()) returns a list of unique lesson names
            lesson_text = "/".join(set(msgs.values()))
            if len(msgs) == 1 and list(msgs.keys())[0] != "grupa_0":
                # Specify the group the current lesson is for if only one group has it
                lesson_text += " " + group_names[list(msgs.keys())[0]]
            new_status_msg = f"{lesson_text} do {util.get_formatted_period_time(current_period).split('-')[1]}"
    else:
        # After the last lesson for the given day
        current_period = -1
        new_status_msg = "koniec lekcji!" if query_time.weekday() < Weekday.friday else "weekend!"
    util.send_log(f"... new status message is '{new_status_msg}'.")
    return new_status_msg


async def remind_about_homework_event(event: homework.HomeworkEvent, tense: str) -> None:
    mention_text = "@everyone"  # To be used at the beginning of the reminder message
    event_name = event.title
    for role in role_codes:
        if role == event.group:
            mention_role = discord.utils.get(my_server.roles, name=role_codes[role])
            if role != "grupa_0":
                mention_text = my_server.get_role(mention_role.id).mention
            break
    target_channel = util.client.get_channel(ChannelID.bot_testing if use_bot_testing else ChannelID.nauka)
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
        return reaction_user != util.client.user and str(test_reaction.emoji) in emojis

    async def snooze_event():
        new_reminder_time = datetime.datetime.now() + datetime.timedelta(hours=1)
        event.reminder_date = new_reminder_time.strftime("%d.%m.%Y %H")
        await message.edit(content=":alarm_clock: Przełożono powiadomienie dla zadania `" +
                                   f"{event_name}` na {str(new_reminder_time.hour).zfill(2)}:00.")

    try:
        reaction, user = await util.client.wait_for('reaction_add', timeout=120.0, check=check_for_valid_reaction)
    except asyncio.TimeoutError:  # 120 seconds have passed with no user input
        await snooze_event()
    else:
        if str(reaction.emoji) == emojis[0]:
            # Reaction emoji is ':ballot_box_with_check:'
            event.reminder_is_active = False
            await message.edit(content=f"{Emoji.check_2} Zaznaczono zadanie `{event_name}` jako odrobione.")
        else:  # Reaction emoji is :alarm_clock:
            await snooze_event()
    await message.clear_reactions()
    file_manager.save_data_file()  # Updates data.json so that if the bot is restarted the event's parameters are saved


@loop(seconds=1)
async def track_time_changes() -> None:
    current_time = datetime.datetime.now()  # Today's time
    tomorrow = datetime.date.today() + datetime.timedelta(days=1)  # Today's date + 1 day
    # Checks if current time is in list of key times
    if current_time.second == 0:
        if any([current_time.hour, current_time.minute] in times for times in util.lesson_plan["Godz"]):
            # Check is successful, bot updates Discord status
            status = discord.Activity(type=discord.ActivityType.watching, name=get_new_status_msg())
            await util.client.change_presence(activity=status)
    # Checks if the bot should make a reminder about due homework
    for event in homework.homework_events:
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


@loop(minutes=1)
async def track_api_updates() -> None:
    for item in steam_market.tracked_market_items:
        await asyncio.sleep(3)
        result = steam_api.get_item(item.name)
        price = steam_api.get_item_price(result)
        # Strips the price string of any non-digit characters and returns it as an integer
        price = int(''.join([char if char in "0123456789" else '' for char in price]))
        if item.min_price < price < item.max_price:
            continue
        target_channel = util.client.get_channel(ChannelID.bot_testing if use_bot_testing else ChannelID.admini)
        await target_channel.send(f"{Emoji.cash} Uwaga, <@{item.author_id}>! "
                                  f"Przedmiot *{item.name}* kosztuje teraz **{price/100:.2f}zł**.")
        steam_market.tracked_market_items.remove(item)
        file_manager.save_data_file()
    await asyncio.sleep(3)
    # Update the lucky numbers cache, and if it's changed, announce the new numbers in the specified channel.
    try:
        old_cache = lucky_numbers_api.update_cache()
    except util.web_api.InvalidResponseException as e:
        # Ping @Konrad
        await util.client.get_channel(ChannelID.bot_logs).send(f"<@{member_ids[8 - 1]}>")
        exc: str = util.format_exception(e)
        util.send_log(f"Error! Received an invalid response from the web request (lucky numbers cache update). Exception trace:\n{exc}")
    else:
        if old_cache != lucky_numbers_api.cached_data:
            util.send_log(f"New lucky numbers data!")
            target_channel = util.client.get_channel(ChannelID.bot_testing if use_bot_testing else ChannelID.general)
            await target_channel.send(embed=commands.lucky_numbers.get_lucky_numbers_embed()[1])
            file_manager.save_data_file()
    try:
        old_cache = file_manager.cache_exists("subs")
        substitutions, cache_existed = substitutions_crawler.get_substitutions(True)
    except util.web_api.InvalidResponseException as e:
        # Ping @Konrad
        await util.client.get_channel(ChannelID.bot_logs).send(f"<@{member_ids[8 - 1]}>")
        exc: str = util.format_exception(e)
        util.send_log(f"Error! Received an invalid response from the web request (substitutions cache update). Exception trace:\n{exc}")
    else:
        if not cache_existed:
            util.send_log(f"Substitution data updated! New data:\n{substitutions}\n\nOld data:\n{old_cache}")
            target_channel = util.client.get_channel(ChannelID.bot_testing if use_bot_testing else ChannelID.general)
            # await target_channel.send(embed=get_substitutions_embed()[1])


@track_api_updates.before_loop
@track_time_changes.before_loop
async def wait_until_ready_before_loops() -> None:
    await util.client.wait_until_ready()


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

    "plan": """Pokazuje plan lekcji dla danego dnia, domyślnie naszej klasy oraz na dzień dzisiejszy.
    Parametry: __dzień tygodnia__, __nazwa klasy__
    Przykłady:
    `{p}plan` - wyświetliłby się plan lekcji na dziś/najbliższy dzień szkolny.
    `{p}plan 2` - wyświetliłby się plan lekcji na wtorek (2. dzień tygodnia).
    `{p}plan pon` - wyświetliłby się plan lekcji na poniedziałek.
    `{p}plan pon 1a` - wyświetliłby się plan lekcji na poniedziałek dla klasy 1a.""",

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

    "num": "Alias komendy `{p}numerki`.",

    "zast": "Podaje zastępstwa na dany dzień."
}

# noinspection SpellCheckingInspection
automatic_bot_replies = {
    "co jest?": "nie wjem"
}


async def wait_for_zadania_reaction(message: discord.Message, reply_msg: discord.Message) -> None:
    def check_for_valid_reaction(test_reaction, reaction_author):
        return str(test_reaction.emoji) == Emoji.unicode_detective and reaction_author != util.client.user

    await reply_msg.add_reaction(Emoji.unicode_detective)
    try:
        await util.client.wait_for('reaction_add', timeout=10.0, check=check_for_valid_reaction)
    except asyncio.TimeoutError:
        # 10 seconds have passed with no user input
        await reply_msg.clear_reactions()
    else:
        # Someone has added detective reaction to message
        await reply_msg.clear_reactions()
        await reply_msg.edit(embed=homework.get_homework_events(message, True)[1])


async def try_send_message(user_message: discord.Message, should_reply: bool, send_args: dict, on_fail_data, on_fail_msg: str = None) -> discord.message:
    send_method = user_message.reply if should_reply else user_message.channel.send
    try:
        reply_msg = await send_method(**send_args)
    except discord.errors.HTTPException:
        util.send_log("Message too long. Length of data:", len(str(on_fail_data)))
        reply_msg = await send_method(on_fail_msg or "Komenda została wykonana pomyślnie, natomiast odpowiedź jest zbyt długa. Załączam ją jako plik tekstowy.")
        with open("result.txt", 'w') as file:
            if type(on_fail_data) is discord.Embed:
                on_fail_data = on_fail_data.to_dict()
            try:
                json.dump(on_fail_data, file, indent=2, ensure_ascii=False)
            except TypeError:
                file.write(str(on_fail_data))
        await user_message.channel.send(file=discord.File("result.txt"))
    return reply_msg


# This method is called when someone sends a message in the server
@util.client.event
async def on_message(message: discord.Message) -> None:
    await util.client.wait_until_ready()
    if util.client.user in message.mentions:
        message.content = "!help " + message.content
    for reply in automatic_bot_replies:
        if reply.lower().startswith(message.content) and len(message.content) >= 3:
            await message.reply(automatic_bot_replies[reply], mention_author=False)
            return
    author_role_names = [str(role) for role in message.author.roles]
    if message.author == util.client.user or "Bot" in author_role_names or not message.content.startswith(prefix):
        return
    if not any(group_role in author_role_names for group_role in ["Grupa 1", "Grupa 2"]):
        await message.channel.send(
            f"{Emoji.warning} **Uwaga, {message.author.mention}: nie posiadasz rangi ani do grupy pierwszej "
            f"ani do grupy drugiej.\nUstaw sobie grupę, do której należysz reagując na wiadomość w kanale "
            f"{util.client.get_channel(773135499627593738).mention} numerem odpowiedniej grupy.**\n"
            f"Możesz sobie tam też ustawić język, na który chodzisz oraz inne rangi.")
    msg_first_word = message.content.lower().lstrip(prefix).split(" ")[0]
    admin_commands = ["exec", "restart", "quit", "exit"]
    if msg_first_word in admin_commands:
        if message.author != util.client.get_user(member_ids[8 - 1]):
            author_name = message.author.nick or message.author.name
            await message.reply(f"Ha ha! Nice try, {author_name}.")
            return
        if msg_first_word == admin_commands[0]:
            if not message.content.startswith(prefix + "exec "):
                await message.channel.send("Type an expression or command to execute.")
                return
            expression = message.content[len(prefix + "exec "):]
            util.send_log("Executing code:", expression)
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
                exec_result = util.format_exception(e)
            if exec_result is None:
                await message.channel.send("Code executed.")
            else:
                expr = expression.replace("\n", "\n>>> ")
                result = exec_result
                if type(exec_result) in [dict, list]:
                    try:
                        result = "```\nDetected JSON content:```json\n" + json.dumps(exec_result, indent=4, ensure_ascii=False)
                    except (TypeError, OverflowError):
                        pass
                too_long_msg = f"Code executed:\n```py\n>>> {expr}```*Result too long to send in message, attaching file 'result.txt'...*"
                success_reply = f"Code executed:\n```py\n>>> {expr}\n{result}\n```"
                await try_send_message(message, False, {"content": success_reply }, exec_result, on_fail_msg=too_long_msg)
            return

        if msg_first_word == admin_commands[1]:
            await message.channel.send("Restarting bot...")
        else:
            await message.channel.send("Exiting program.")
            file_manager.log(f"\n    --- Program manually closed by user ('{msg_first_word}' command). ---")
            global restart_on_exit
            restart_on_exit = False
        track_time_changes.stop()
        track_api_updates.stop()
        await util.client.close()

    if msg_first_word not in help.info:
        return
    # await message.delete()

    util.send_log(f"Received command: '{message.content}'", "from user:", message.author)
    command_method_to_call_when_executed = help.info[msg_first_word]["method"]
    try:
        reply_is_embed, reply = command_method_to_call_when_executed(message)
    except Exception as e:
        util.send_log(util.format_exception(e))
        await message.reply(f"<@{member_ids[8 - 1]}> An exception occurred while executing command `{message.content}`."
                            f" Check the bot logs for details.")
        return
    reply_msg = await try_send_message(message, True, {"embed" if reply_is_embed else "content": reply}, reply)
    if msg_first_word == "zadania":
        await wait_for_zadania_reaction(message, reply_msg)


def start_bot() -> bool:
    """Log in to the Discord bot and start its functionality.
    This method is blocking -- once the bot is connected, it will run until it's disconnected.

    Returns a boolean that indicates if the bot should be restarted.
    """
    # Save the previous log on startup
    file_manager.save_log_file()
    save_on_exit = True
    # Update each imported module before starting the bot.
    # The point of restarting the bot is to update the code without having to manually stop and start the script.
    for module in (file_manager, steam_api, util.web_api, lucky_numbers_api, plan_crawler, substitutions_crawler):
        importlib.reload(module)
    try:
        file_manager.read_env_file()
        file_manager.read_data_file('data.json')
        event_loop = asyncio.get_event_loop()
        try:
            token = os.environ["BOT_TOKEN"]
        except KeyError:
            file_manager.log("\n    --- CRITICAL ERROR! ---")
            file_manager.log("'BOT_TOKEN' OS environment variable not found. Program exiting.")
            save_on_exit = False
            # Do not restart bot
            return False
        else:
            # No problems finding OS variable containing bot token. Can login successfully.
            event_loop.run_until_complete(util.client.login(token))
        # Bot has been logged in, continue with attempt to connect
        try:
            # Blocking call:
            # The program will stay on this line until the bot is disconnected.
            event_loop.run_until_complete(util.client.connect())
        except KeyboardInterrupt:
            # Raised when the program is forcefully closed (eg. Ctrl+F2 in PyCharm).
            file_manager.log("\n    --- Program manually closed by user (KeyboardInterrupt exception). ---")
            # Do not restart, since the closure of the bot was specifically requested by the user.
            return False
        else:
            # The bot was exited gracefully (eg. !exit, !restart command issued in Discord)
            file_manager.log("\n    --- Bot execution terminated successfully. ---")
    finally:
        # Execute this no matter the circumstances, ensures data file is always up-to-date.
        if save_on_exit:
            # The file is saved before the start_bot() method returns any value.
            # Do not send a debug message since the bot is already offline.
            file_manager.save_data_file(should_log=False)
            file_manager.log("Successfully saved data file 'data.json'. Program exiting.")
    # By default, when the program is exited gracefully (see above), it is later restarted in 'run.pyw'.
    # If the user issues a command like !exit, !quit, the return_on_exit global variable is set to False,
    # and the bot is not restarted.
    return restart_on_exit


if __name__ == "__main__":
    file_manager.log("Started bot from main file! Assuming this is debug behaviour.\n")
    use_bot_testing = True
    enable_log_messages = True
    start_bot()
