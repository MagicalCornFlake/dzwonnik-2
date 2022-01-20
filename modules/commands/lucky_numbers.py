"""Module containing code relating to the 'num' command."""

# Standard library imports
from datetime import datetime

# Third-party imports
from discord import Message, Embed

# Local application imports
from .. import bot, util, MEMBER_IDS
from ..util import web
from ..util.api import lucky_numbers as numbers_api


DESC = """Podaje aktualne szczęśliwe numerki oraz klasy, które są z nich wykluczone."""


def get_lucky_numbers_embed(_: Message = None) -> Embed or str:
    """Event handler for the 'num' command."""
    try:
        data = numbers_api.get_lucky_numbers()
    except web.WebException as web_exc:
        exc: str = util.format_exception_info(web_exc)
        bot.send_log(f"{bot.BAD_RESPONSE}{exc}", force=True)
        return web.get_error_message(web_exc)
    date_str: str = datetime.strftime(data["date"], "%d.%m.%Y")
    msg = f"Szczęśliwe numerki na {date_str}:"
    embed = Embed(title="Szczęśliwe numerki", description=msg)
    footer_text = f"Użyj komendy {bot.prefix}numerki, aby pokazać tą wiadomość."
    embed.set_footer(text=footer_text)
    for num in data["luckyNumbers"]:
        try:
            member_text = MEMBER_IDS[num - 1]
        except IndexError:
            member_text = f"*W naszej klasie nie ma osoby z numerkiem __{num}__.*"
        else:
            if isinstance(member_text, int):
                # Wrap the ID in a Discord ping
                member_text = f"<@!{member_text}>"
        embed.add_field(name=num, value=member_text, inline=False)
    # embed.add_field(name="\u200B", value="\u200B", inline=False)
    excluded = ", ".join(data["excludedClasses"]) or "*Brak*"
    embed.add_field(name="Wykluczone klasy", value=excluded, inline=False)
    return embed
