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


def get_substitutions_embed(message: Message = None) -> tuple[bool, Embed or str]:
    try:
        data = substitutions_crawler.get_substitutions(message is None)[0]
    except Exception as e:
        ex: str = util.format_exception_info(e)
        bot.send_log(f"Error! Received an invalid response from the web request. Exception trace:\n{ex}", force=True)
        return False, web.get_error_message(e)
    msg = f"Zastępstwa na {datetime.now():%d.%m.%Y}:"
    embed = Embed(title="Zastępstwa", description=msg)
    embed.add_field(name="Dane", value=data, inline=False)
    embed.set_footer(text=f"Użyj komendy {bot.prefix}zast, aby pokazać tą wiadomość.")
    return True, embed
