"""Module containing the code pertaining to the 'restart' and 'exit' commands."""

# Third-party imports
import discord


# Local application imports
from modules.commands import ensure_user_authorised
from .. import bot, file_manager
DESC = None


RESTARTING_BOT_MSG = "Restarting bot..."
EXITING_BOT_MSG = "Exiting program."


def restart_bot(message: discord.Message) -> str:
    """Event handler for the 'restart' command."""
    ensure_user_authorised(message, owner_only=True)
    return RESTARTING_BOT_MSG


def exit_bot(message: discord.Message) -> str:
    """Event handler for the 'exit' command."""
    ensure_user_authorised(message, owner_only=True)
    bot.restart_on_exit = False
    return EXITING_BOT_MSG


async def terminate_bot(original_msg: discord.Message, reply_msg: discord.Message) -> None:
    """Save's the ID of the bot's exit message and terminates the bot client process."""
    file_manager.on_exit_msg = {
        "is_restart": reply_msg.content == RESTARTING_BOT_MSG,
        "channel_id": original_msg.channel.id,
        "message_id": reply_msg.id
    }
    bot.main_update_loop.stop()
    await bot.close()
