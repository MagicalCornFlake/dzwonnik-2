"""Module containing the code for handling the prefix command to change the bot's command prefix."""

# Third-party imports
from discord import Message, TextChannel

# Local application imports
from .. import Emoji, bot


def change_prefix(message: Message) -> tuple[bool, str]:
    args: list[str] = message.content.split(" ")
    if len(args) < 2:
        msg: str = f"{Emoji.warning} Należy po komendzie `{bot.prefix}prefix wpisać nowy prefiks dla komend."
        return False, msg
    old_prefix: str = bot.prefix
    bot.prefix = args[1]
    return False, f"{Emoji.check} Zmieniono prefiks dla komend z `{old_prefix}` na `{args[1]}`."

async def ask_for_confirmation(channel: TextChannel, new_prefix) -> bool:
    question = channel.send(f"Czy na pewno chcesz zmienić prefiks dla komend na: `{new_prefix}`?")
    question.add_reaction()
