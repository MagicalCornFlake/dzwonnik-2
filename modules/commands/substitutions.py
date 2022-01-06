"""Module containing code relating to the 'zast' command."""

# Standard library imports
from datetime import datetime

# Third-party imports
from discord import Message, Embed

# Local application imports
from .. import bot, util
from ..util import web
from ..util.crawlers import substitutions as substitutions_crawler


desc = "Podaje zastępstwa na dany dzień."


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

    # Initialise the embed
    date = datetime.strptime(data["date"], "%Y-%m-%d")
    description = f"Zastępstwa na {date:%d.%m.%Y}:"
    embed = Embed(title="Zastępstwa", description=description)
    footer = f"Użyj komendy {bot.prefix}zast, aby pokazać tą wiadomość."
    embed.set_footer(text=footer)

    # Add fields
    teachers = ', '.join(data["teachers"])
    embed.add_field(name="Nauczyciele", value=teachers, inline=False)
    events = '\n'.join(data["events"])
    embed.add_field(name="Wydarzenia szkolne", value=events, inline=False)

    for period in data["lessons"]:
        class_msgs = []
        for class_name, substitutions in data["lessons"][period].items():
            sub_msgs = []
            for sub_info in substitutions:
                groups = sub_info.get("groups")
                group_text = f"(gr. {', '.join(groups)}) — " if groups else ""
                sub_msgs.append(f"{group_text}*{sub_info['details']}*")
            standard_msg = f"**{class_name}**: {' | '.join(sub_msgs)}"
            hyperlinked_msg = f"[{standard_msg}]({substitutions_crawler.source_url})"
            formatted_class_msg = hyperlinked_msg if class_name == util.format_class() else standard_msg
            class_msgs.append(formatted_class_msg)
        time = util.get_formatted_period_time(period)
        field_args = {
            "name": f"Lekcja {period} ({time})",
            "value": '\n'.join(class_msgs)
        }
        embed.add_field(**field_args, inline=False)
    for table in data["tables"]:
        field_args = {
            "name": table["heading"],
            "value": f"{table['rows']} lekcje",
        }
        embed.add_field(**field_args, inline=False)
    embed.add_field(name="Lekcje odwołane", value=data["cancelled"])
    return True, embed
