"""Module containing code relating to the 'num' command."""

# Third-party imports
from discord import Message, Embed

# Local application imports
from .. import prefix, member_ids
from .. util import get_web_api_error_message, format_exception
from .. util.api.lucky_numbers_api import get_lucky_numbers
from .. file_manager import send_log


def get_lucky_numbers_embed(_: Message = None) -> tuple[bool, Embed or str]:
    try:
        data = get_lucky_numbers()
    except Exception as e:
        exc: str = format_exception(e)
        send_log(f"Error! Received an invalid response from the web request. Exception trace:\n{exc}")
        return False, get_web_api_error_message(e)
    msg = f"Szczęśliwe numerki na {data['date']}:"
    embed = Embed(title="Szczęśliwe numerki", description=msg)
    for n in data["luckyNumbers"]:
        member_text = f"*W naszej klasie nie ma osoby z numerkiem __{n}__.*" if n > len(member_ids) else \
            f"<@!{member_ids[n - 1]}>" if type(member_ids[n - 1]) is int else member_ids[n - 1]
        embed.add_field(name=n, value=member_text, inline=False)
    # embed.add_field(name="\u200B", value="\u200B", inline=False)
    excluded_classes = ", ".join(data["excludedClasses"]) if len(data["excludedClasses"]) > 0 else "*Brak*"
    embed.add_field(name="Wykluczone klasy", value=excluded_classes, inline=False)
    embed.set_footer(text=f"Użyj komendy {prefix}numerki, aby pokazać tą wiadomość.")
    return True, embed
