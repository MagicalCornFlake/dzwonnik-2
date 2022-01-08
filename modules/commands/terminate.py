"""Module containing the code pertaining to the 'restart', 'stop' and 'exit' commands."""

# Third-party imports
import discord


# Local application imports
from .. import bot, file_manager
from modules.commands import ensure_sender_is_admin
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


async def terminate_bot(original_msg: discord.Message, reply_msg: discord.Message) -> None:
    """Save's the ID of the bot's exit message and terminates the bot client process."""
    command_content: str = original_msg.content
    is_restart = command_content.startswith(f"{bot.prefix}restart")
    file_manager.on_exit_msg = {
        "is_restart": is_restart,
        "channel_id": reply_msg.channel.id,
        "message_id": reply_msg.id
    }
    bot.main_update_loop.stop()
    await bot.close()
