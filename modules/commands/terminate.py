"""Module containing the code pertaining to the 'restart', 'stop' and 'exit' commands."""

# Third-party imports
import discord

from modules.commands import ensure_sender_is_admin

# Local application imports
from .. import file_manager, bot
DESC = None


def restart_bot(message: discord.Message) -> tuple[bool, str]:
    ensure_sender_is_admin(message)
    return False, "Restarting bot..."


def exit_bot(message: discord.Message) -> tuple[bool, str]:
    """Ensures that the bot is not restarted after the process is terminated."""
    message_content: str = message.content
    cmd = message_content.lstrip(bot.prefix)
    ensure_sender_is_admin(message)
    log_msg = f"    --- Program manually closed by user ('{cmd}' command). ---"
    file_manager.log(log_msg)
    bot.restart_on_exit = False
    return False, "Exiting program."


async def terminate_bot():
    """Terminates the bot client process."""
    bot.main_update_loop.stop()
    await bot.set_offline_status()
    await bot.client.close()
    file_manager.log("Bot disconnected.")
