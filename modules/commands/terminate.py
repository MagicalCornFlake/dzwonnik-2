"""Module containing the code pertaining to the 'restart', 'stop' and 'exit' commands."""

# Third-party imports
import discord

from modules.commands import ensure_sender_is_admin

# Local application imports
from .. import bot
DESC = None


def restart_bot(message: discord.Message) -> tuple[bool, str]:
    """Event handler for the 'restart' command."""
    ensure_sender_is_admin(message)
    return False, "Restarting bot..."


def exit_bot(message: discord.Message) -> tuple[bool, str]:
    """Event handler for the 'exit' command."""
    ensure_sender_is_admin(message)
    bot.restart_on_exit = False
    return False, "Exiting program."


async def terminate_bot(_original_msg: discord.Message, _reply_msg: discord.Message) -> None:
    """Terminates the bot client process."""
    bot.main_update_loop.stop()
    await bot.close()
