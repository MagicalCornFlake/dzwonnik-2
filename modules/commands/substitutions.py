"""Module containing code relating to the 'zast' command."""

# Standard library imports
from datetime import datetime

# Third-party imports
import discord
from corny_commons import util as ccutil
from corny_commons.util import web

# Local application imports
from modules import bot, util
from modules.api import substitutions


DESC = """Podaje zastępstwa na dany dzień."""

BAD_SUBSTITUTIONS_MSG = ":x: Nie udało się odzyskać zastępstw. Proszę spróbowac ponownie w krótce."
FOOTER_TEMPLATE = "Użyj komendy {}zast, aby pokazać tą wiadomość."
DESC_TEMPLATE = "Liczba zastępstw dla klasy {}: **{}**"


# Data to be stored between functions while the command is executing
temp_data: dict[str, any] = {}


def add_substitution_text_fields(embed: discord.Embed, data: dict, source_url: str) -> int:
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
            inline=False
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

    # Initialise the embed
    url = f"{substitutions.SOURCE_URL}#{data['post'].get('id', 'content')}"
    embed = discord.Embed(
        title=f"Zastępstwa na {datetime.strptime(data['date'], '%Y-%m-%d'):%d.%m.%Y}",
        url=url
    ).set_footer(text=FOOTER_TEMPLATE.format(bot.prefix))

    # Add fields
    embed.add_field(
        name="Nauczyciele",
        value=', '.join(data["teachers"]),
        inline=False
    ).add_field(
        name="Wydarzenia szkolne",
        value="\n".join(data["events"]) or "*Brak*",
        inline=False
    )

    # Set embed description to contain the number of substitutions for our class
    embed.description = DESC_TEMPLATE.format(
        util.OUR_CLASS,
        add_substitution_text_fields(embed, data, url)
    )

    # Cancelled lessons field
    cancelled = data.get("cancelled")
    if cancelled:
        embed.add_field(name="Lekcje odwołane",
                        value="\n".join(cancelled))

    # School events fields
    for table in data["tables"]:
        for col in range(len(table["headings"])):
            rows = table["columns"][col]
            if col == 0:
                rows = ', '.join([f"**{r}**" for r in rows])
                desc = f"*Odpowiednio: {rows}*"
                embed.add_field(name=table["title"], value=desc, inline=False)
                continue
            heading = table["headings"][col]
            field_args = {
                "name": heading,
                "value": "\n".join(rows)
            }
            embed.add_field(**field_args, inline=True)

    # Miscellaneous information field
    misc_info = data.get("misc")
    if misc_info:
        embed.add_field(
            name="Informacje dodatkowe",
            value="\n".join(misc_info),
            inline=False
        )
    # Check if the data was updated
    if data != old_data:
        temp_data["embed"] = embed
    return embed


async def announce_new_substitutions() -> None:
    """Callback to be run after the command is executed. Announces the substitutions if new."""
    try:
        await bot.announce_substitutions(temp_data["embed"])
    except KeyError:
        # The substitutions were not changed. Don't announce them.
        pass
    finally:
        temp_data.clear()
