"""Module containing code relating to the 'zast' command."""

# Standard library imports
from datetime import datetime

# Third-party imports
import discord
from corny_commons import util as ccutil
from corny_commons.util import web

# Local application imports
from modules import bot, util, WEEKDAY_NAMES
from modules.api import substitutions


DESC = """Podaje zastępstwa na dany dzień."""

BAD_SUBSTITUTIONS_MSG = (
    ":x: Nie udało się odzyskać zastępstw. Proszę spróbowac ponownie w krótce."
)
FOOTER_TEMPLATE = "Użyj komendy {}zast, aby pokazać tą wiadomość."
DESC_TEMPLATE = "Liczba zastępstw dla klasy {}: **{}**"


# Data to be stored between functions while the command is executing
temp_data: dict[str, bool] = {}


def get_all_lessons_on_day(weekday: int) -> list[dict[str, str]]:
    """Gets all the lessons taking place on a given day of the week."""
    plan = util.lesson_plan_dp["weekdays"][weekday]
    lessons = []
    for block in plan:
        lessons += block["lessons"]
    return lessons


def get_lessons_with_teacher(
    raw_teacher: str, lessons: list[dict[str, str]]
) -> tuple[str, list]:
    """Filters the lessons to those taking place with the given teacher.

    Returns the teacher's unconjugated surname form as well as a list of their lessons."""
    mappings = {"ą": "a", "im": "i", "iem": ""}

    # De-conjugate the teacher surnames
    def map_word_part(part):
        for ending, new_ending in mappings.items():
            if not part.endswith(ending):
                continue
            return part[: -len(ending)] + new_ending
        return part

    teacher_name = "-".join(map(map_word_part, raw_teacher.split("-")))
    subjects = util.teacher_subjects.get(teacher_name)
    if not isinstance(subjects, list):
        subjects = [subjects]

    # Get the subjects taught by that teacher on the given day
    result = []
    for lesson in lessons:
        lesson_name = lesson["name"]
        lesson_full_name = f"{lesson_name} {lesson.get('level', '')}".strip()
        if lesson_full_name in subjects or lesson_name in subjects:
            result.append(lesson_full_name)
    return teacher_name, (result or ["brak"])


def add_substitution_text_fields(
    embed: discord.Embed, data: dict, source_url: str
) -> int:
    """Adds the text fields to the substitutions embed.

    Returns the number of substitutions for our class.
    """
    our_substitutions: int = 0
    for period, classes in data["lessons"].items():
        class_msgs = []
        for class_name, class_data in sorted(classes.items()):
            sub_msgs = []
            for sub_info in class_data["substitutions"]:
                groups = sub_info.get("groups")
                groups = f"gr. {', '.join(groups)} — " if groups else ""
                sub_msgs.append(f"{groups}*{sub_info['details']}*")
            lessons = class_data["substituted_lessons"]
            lessons = [util.format_lesson_info(lesson) for lesson in lessons]
            # Stylise the substituted lessons as crossed out; default to "" if list empty
            lessons = f"~~{'; '.join(lessons)}~~" if lessons else ""
            substitution_text = f"**{class_name}**: {lessons} {' | '.join(sub_msgs)}"

            if class_name != util.format_class():
                class_msgs.append(substitution_text)
                continue
            our_substitutions += 1
            class_msgs.append(f"[{substitution_text}]({source_url})")
        embed.add_field(
            name=f"Lekcja {period} ({util.get_formatted_period_time(period)})",
            value="\n".join(class_msgs),
            inline=False,
        )
    return our_substitutions


def get_substitutions_embed(_: discord.Message = None) -> discord.Embed or str:
    """Event handler for the 'zast' command."""
    try:
        data, old_data = substitutions.get_substitutions()
    except web.WebException as web_exc:
        ex: str = ccutil.format_exception_info(web_exc)
        bot.send_log(f"{bot.BAD_RESPONSE}{ex}", force=True)
        return util.get_error_message(web_exc)
    else:
        # Ensure the data is valid
        if "error" in data or not {"teachers", "date", "events"}.issubset(data):
            return BAD_SUBSTITUTIONS_MSG
        # Check if the data was updated
        if data != old_data:
            temp_data["updated_for_same_day"] = data.get("date") == old_data.get("date")

    # Initialise the embed
    url = f"{substitutions.SOURCE_URL}#{data['post'].get('id', 'content')}"
    embed = discord.Embed(
        title=f"Zastępstwa na {datetime.strptime(data['date'], '%Y-%m-%d'):%d.%m.%Y}",
        url=url,
    ).set_footer(text=FOOTER_TEMPLATE.format(bot.prefix))

    # Add fields
    embed.add_field(
        name="Nauczyciele", value=", ".join(data["teachers"]), inline=False
    ).add_field(
        name="Wydarzenia szkolne",
        value="\n".join(data["events"]) or "*Brak*",
        inline=False,
    )

    # Set embed description to contain the number of substitutions for our class
    embed.description = DESC_TEMPLATE.format(
        util.OUR_CLASS, add_substitution_text_fields(embed, data, url)
    )

    # Cancelled lessons field
    cancelled = data.get("cancelled")
    if cancelled:
        embed.add_field(name="Lekcje odwołane", value=" ".join(cancelled))

    # School events fields
    for table in data["tables"]:
        for col in range(len(table["headings"])):
            rows = table["columns"][col]
            if col == 0:
                rows = ", ".join([f"**{r}**" for r in rows])
                desc = f"*Odpowiednio: {rows}*"
                embed.add_field(name=table["title"], value=desc, inline=False)
                continue
            heading = table["headings"][col]
            field_args = {"name": heading, "value": "\n".join(rows)}
            embed.add_field(**field_args, inline=True)

    # Miscellaneous information field
    misc_info = data.get("misc")
    if misc_info:
        embed.add_field(
            name="Informacje dodatkowe", value="\n".join(misc_info), inline=False
        )
    return embed


def get_new_substitutions_embed(_: discord.Message = None) -> discord.Embed or str:
    """Event handler for the 'zast' command, following the new substitutions format."""
    try:
        data, old_data = substitutions.get_substitutions()
    except web.WebException as web_exc:
        ex: str = ccutil.format_exception_info(web_exc)
        bot.send_log(f"{bot.BAD_RESPONSE}{ex}", force=True)
        return util.get_error_message(web_exc)
    else:
        # Check if the data was updated
        if data != old_data:
            temp_data["updated_for_same_day"] = data.keys() == old_data.keys()

    # Initialise the embed
    dates = sorted(data.keys(), key=lambda x: datetime.strptime(x, "%d.%m.%Y"))
    embed = discord.Embed(
        title=f"Zastępstwa na {', '.join(dates)}",
        url=f"{substitutions.SOURCE_URL}#content",
    ).set_footer(text=FOOTER_TEMPLATE.format(bot.prefix))

    for date in dates:
        weekday = datetime.strptime(date, "%d.%m.%Y").weekday()
        all_lessons = get_all_lessons_on_day(weekday)
        teachers_msg = "*Następujące zajęcia są odwołane:*\n"
        for teacher in data[date]:
            teacher_name, lessons = get_lessons_with_teacher(teacher, all_lessons)
            teachers_msg += f"p. {teacher_name} — {', '.join(lessons)}\n"
        embed.add_field(
            name=f"{WEEKDAY_NAMES[weekday]} {date}",
            value=teachers_msg,
            inline=False,
        )

    return embed


async def announce_new_substitutions(
    _: discord.Message, bot_reply: discord.Message
) -> None:
    """Callback to be run after the command is executed. Announces the substitutions if new."""
    updated_for_same_day: bool or None = temp_data.get("updated_for_same_day")
    if updated_for_same_day is None:
        # The substitutions were not changed. Don't announce them.
        return
    try:
        embed = bot_reply.embeds[0]
        if not isinstance(embed, discord.Embed):
            raise ValueError
    except (IndexError, ValueError):
        bot.send_log(
            "Error! Could not send the substitutions announcement embed.", force=True
        )
    else:
        await bot.announce_substitutions(embed, same_day=updated_for_same_day)
    temp_data.clear()
