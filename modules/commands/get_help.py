"""Module containing code relating to the 'help' command."""

# Third-party imports
from discord import Message, Embed

# Local application imports
from modules import bot
from modules.commands import next_lesson, next_break, plan, homework, steam_market
from modules.commands import meet, exec as execute, terminate, lucky_numbers, substitutions


def get_help_message(message: Message) -> Embed or None:
    """Event handler for the 'help' command."""
    msg_content: str = message.content
    if not msg_content.rstrip().lower().endswith("help"):
        return None
    desc = f"Prefiks dla komend: `{bot.prefix}`"
    embed = Embed(title="Lista komend", description=desc)
    for command_name, info in INFO.items():
        command_description = info["description"]
        if not command_description:
            continue
        cmd_desc = command_description.format(p=bot.prefix)
        embed.add_field(name=command_name, value=cmd_desc, inline=False)
    footer = f"Użyj komendy {bot.prefix}help lub mnie @oznacz, aby pokazać tą wiadomość."
    embed.set_footer(text=footer)
    return embed


INFO: dict[help, dict[str, any]] = {
    "help": {
        "description": "Wyświetla tą wiadomość.",
        "function": get_help_message
    },
    "nl": {
        "description": next_lesson.DESC,
        "function": next_lesson.get_next_lesson
    },
    "nb": {
        "description": next_break.DESC,
        "function": next_break.get_next_break
    },
    "plan": {
        "description": plan.DESC,
        "function": plan.get_lesson_plan
    },
    "zad": {
        "description": homework.DESC,
        "function": homework.process_homework_events_alias
    },
    "zadanie": {
        "description": homework.DESC_CREATE,
        "function": homework.create_homework_event
    },
    "zadania": {
        "description": homework.DESC_LIST,
        "function": homework.get_homework_events,
        "on_completion": homework.wait_for_zadania_reaction
    },
    "cena": {
        "description": steam_market.DESC,
        "function": steam_market.get_market_price
    },
    "sledz": {
        "description": steam_market.DESC_TRACK,
        "function": steam_market.start_market_tracking
    },
    "odsledz": {
        "description": steam_market.DESC_UNTRACK,
        "function": steam_market.stop_market_tracking
    },
    "numerki": {
        "description": lucky_numbers.DESC,
        "function": lucky_numbers.get_lucky_numbers_embed
    },
    "num": {
        "description": "Alias komendy `{p}numerki`.",
        "function": lucky_numbers.get_lucky_numbers_embed
    },
    "zast": {
        "description": substitutions.DESC,
        "function": substitutions.get_substitutions_embed,
        "on_completion": substitutions.announce_new_substitutions
    },
    "meet": {
        "description": meet.DESC,
        "function": meet.update_meet_link
    },
    "exec": {
        "description": execute.DESC,
        "function": execute.exec_command_handler,
        "on_completion": execute.execute_code
    },
    "restart": {
        "description": terminate.DESC,
        "function": terminate.restart_bot,
        "on_completion": terminate.terminate_bot
    },
    "exit": {
        "description": terminate.DESC,
        "function": terminate.exit_bot,
        "on_completion": terminate.terminate_bot
    }
}
