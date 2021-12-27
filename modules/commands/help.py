"""Module containing code relating to the 'help' command."""

# Third-party imports
from discord import Message, Embed

# Local application imports
from . import next_lesson, next_break, plan, homework, meet, steam_market, lucky_numbers, substitutions
from .. import bot


def get_help_message(_: Message) -> tuple[bool, Embed]:
    embed = Embed(title="Lista komend", description=f"Prefiks dla komend: `{bot.prefix}`")
    for command_name in info:
        command_description = info[command_name]["description"]
        if command_description:
            embed.add_field(name=command_name, value=command_description.format(p=bot.prefix), inline=False)
    embed.set_footer(text=f"Użyj komendy {bot.prefix}help lub mnie **@oznacz**, aby pokazać tą wiadomość.")
    return True, embed


info: dict[help, dict[str, str or function]] = {
    'help': {
        "description": "Wyświetla tą wiadomość.",
        "function": get_help_message
    },
    'nl': {
        "description": next_lesson.desc,
        "function": next_lesson.get_next_lesson
    },
    'nb': {
        "description": next_break.desc,
        "function": next_break.get_next_break
    },
    'plan': {
        "description": plan.desc,
        "function": plan.get_lesson_plan
    },
    'zad': {
        "description": homework.desc,
        "function": homework.process_homework_events_alias
    },
    'zadanie': {
        "description": homework.desc_2,
        "function": homework.create_homework_event
    },
    'zadania': {
        "description": homework.desc_3,
        "function": homework.get_homework_events
    },
    'meet': {
        "description": meet.desc,
        "function": meet.update_meet_link
    },
    'cena': {
        "description": steam_market.desc,
        "function": steam_market.get_market_price
    },
    'sledz': {
        "description": steam_market.desc_2,
        "function": steam_market.start_market_tracking
    },
    'odsledz': {
        "description": steam_market.desc_3,
        "function": steam_market.stop_market_tracking
    },
    'numerki': {
        "description": lucky_numbers.desc,
        "function": lucky_numbers.get_lucky_numbers_embed
    },
    'num': {
        "description": "Alias komendy `{p}numerki`.",
        "function": lucky_numbers.get_lucky_numbers_embed
    },
    'zast': {
        "description": substitutions.desc,
        "function": substitutions.get_substitutions_embed
    }
}
