"""Module containing code relating to the 'zast' command."""

# Standard library imports
from datetime import datetime

# Third-party imports
from discord import Message, Embed

# Local application imports
from .. import bot, util
from ..util import web
from ..util.crawlers import substitutions as substitutions_crawler


DESC = """Podaje zastępstwa na dany dzień."""


def get_substitutions_embed(_: Message = None) -> tuple[bool, Embed or str]:
    try:
        # No need to set the force argument if the function is called from the API update loop since the cache has already been updated
        data = substitutions_crawler.get_substitutions()[0]
    except Exception as e:
        ex: str = util.format_exception_info(e)
        bot.send_log(f"{bot.bad_response}{ex}", force=True)
        return False, web.get_error_message(e)
    else:
        if "error" in data:
            return False, ":x: Nie można było odzyskać zastępstw. Proszę spróbowac ponownie w krótce."

    # Number of substitutions for our class
    our_substitutions: int = 0

    # Initialise the embed
    date = datetime.strptime(data["date"], "%Y-%m-%d")
    url = substitutions_crawler.SOURCE_URL
    embed = Embed(title=f"Zastępstwa na {date:%d.%m.%Y}", url=url)
    footer = f"Użyj komendy {bot.prefix}zast, aby pokazać tą wiadomość."
    embed.set_footer(text=footer)

    # Add fields
    teachers = ', '.join(data["teachers"])
    embed.add_field(name="Nauczyciele", value=teachers, inline=False)
    events = '\n'.join(data["events"])
    embed.add_field(name="Wydarzenia szkolne", value=events, inline=False)

    # Substitution fields
    for period in data["lessons"]:
        class_msgs = []
        for class_name, substitutions in data["lessons"][period].items():
            sub_msgs = []
            for sub_info in substitutions:
                groups = sub_info.get("groups")
                group_text = f"(gr. {', '.join(groups)}) — " if groups else ""
                sub_msgs.append(f"{group_text}*{sub_info['details']}*")
            standard_msg = f"**{class_name}**: {' | '.join(sub_msgs)}"
            if class_name == util.format_class():
                our_substitutions += 1
                hyperlinked_msg = f"[{standard_msg}]({substitutions_crawler.SOURCE_URL})"
                class_msgs.append(hyperlinked_msg)
                continue
            class_msgs.append(standard_msg)
        time = util.get_formatted_period_time(period)
        field_args = {
            "name": f"Lekcja {period} ({time})",
            "value": '\n'.join(class_msgs)
        }
        embed.add_field(**field_args, inline=False)

    # Cancelled lessons field
    embed.add_field(name="Lekcje odwołane", value=data["cancelled"])

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

    # Set embed description to contain the number of substitutions for our class
    embed.description = f"Liczba zastępstw dla klasy {util.OUR_CLASS}: **{our_substitutions}**"
    return True, embed
