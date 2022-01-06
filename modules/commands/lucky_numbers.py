"""Module containing code relating to the 'num' command."""

# Standard library imports
from datetime import datetime

# Third-party imports
from discord import Message, Embed

# Local application imports
from .. import bot, util, member_ids
from ..util import web
from ..util.api import lucky_numbers as numbers_api


desc = "Podaje aktualne szczęśliwe numerki oraz klasy, które są z nich wykluczone."


def get_lucky_numbers_embed(_: Message = None) -> tuple[bool, Embed or str]:
    try:
        data = numbers_api.get_lucky_numbers()
    except Exception as e:
        exc: str = util.format_exception_info(e)
        bot.send_log(f"{bot.bad_response}{exc}")
        return False, web.get_error_message(e)
    date_str: str = datetime.strftime(data["date"], "%d.%m.%Y")
    msg = f"Szczęśliwe numerki na {date_str}:"
    embed = Embed(title="Szczęśliwe numerki", description=msg)
    footer_text = f"Użyj komendy {bot.prefix}numerki, aby pokazać tą wiadomość."
    embed.set_footer(text=footer_text)
    for n in data["luckyNumbers"]:
        is_id = type(member_ids[n - 1]) is int
        member_text = f"*W naszej klasie nie ma osoby z numerkiem __{n}__.*" if n > len(member_ids) else \
            f"<@!{member_ids[n - 1]}>" if is_id else member_ids[n - 1]
        embed.add_field(name=n, value=member_text, inline=False)
    # embed.add_field(name="\u200B", value="\u200B", inline=False)
    excluded = ", ".join(data["excludedClasses"]) or "*Brak*"
    embed.add_field(name="Wykluczone klasy", value=excluded, inline=False)
    return True, embed
