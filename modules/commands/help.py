"""Module containing code relating to the 'help' command."""

# Third-party imports
from discord import Message, Embed

# Local application imports
from . import info
from .. import prefix

def get_help_message(_: Message) -> tuple[bool, Embed]:
    embed = Embed(title="Lista komend", description=f"Prefiks dla komend: `{prefix}`")
    for command in info:
        if command["description"] is None:
            continue
        embed.add_field(name=command, value=command["description"].format(p=prefix), inline=False)
    embed.set_footer(text=f"Użyj komendy {prefix}help lub mnie @oznacz, aby pokazać tą wiadomość.")
    return True, embed
