"""Module containing the code for handling the prefix command to change the bot's command prefix."""

# Third-party imports
from discord import Message, TextChannel

# Local application imports
from .. import Emoji, bot


DESC = """Zmienia prefiks dla komend."""


def change_prefix(message: Message) -> str:
    """Event handler for the 'prefix' command."""
    args: list[str] = message.content.split(" ")
    if len(args) < 2:
        invalid_args_msg: str = (f"{Emoji.WARNING} Należy po komendzie `{bot.prefix}prefix wpisać"
                                 " nowy prefiks dla komend.")
        return invalid_args_msg
    old_prefix: str = bot.prefix
    bot.prefix = args[1]
    return f"{Emoji.CHECK} Zmieniono prefiks dla komend z `{old_prefix}` na `{args[1]}`."


async def ask_for_confirmation(channel: TextChannel, new_prefix) -> bool:
    """Post-command callback for the 'prefix' command."""
    question = channel.send(f"Czy na pewno chcesz zmienić prefiks dla komend na: `{new_prefix}`?")
    question.add_reaction()
