"""Module containing code relating to the 'help' command."""

# Third-party imports
from discord import Message, Embed

# Local application imports
from . import next_lesson, next_break, plan, homework, meet, steam_market, lucky_numbers, substitutions
from .. import prefix


def get_help_message(_: Message) -> tuple[bool, Embed]:
    embed = Embed(title="Lista komend", description=f"Prefiks dla komend: `{prefix}`")
    for command in info:
        if command["description"] is None:
            continue
        embed.add_field(name=command, value=command["description"].format(p=prefix), inline=False)
    embed.set_footer(text=f"Użyj komendy {prefix}help lub mnie **@oznacz**, aby pokazać tą wiadomość.")
    return True, embed


info = {
    'help': {
        "description": "",
        "method": get_help_message
    },
    'nl': {
        "description": "",
        "method": next_lesson.get_next_lesson
    },
    'nb': {
        "description": "",
        "method": next_break.get_next_break
    },
    'plan': {
        "description": "",
        "method": plan.get_lesson_plan
    },
    'zad': {
        "description": "",
        "method": homework.process_homework_events_alias
    },
    'zadanie': {
        "description": "",
        "method": homework.create_homework_event
    },
    'zadania': {
        "description": "",
        "method": homework.get_homework_events
    },
    'meet': {
        "description": "",
        "method": meet.update_meet_link
    },
    'cena': {
        "description": "",
        "method": steam_market.get_market_price
    },
    'sledz': {
        "description": "",
        "method": steam_market.start_market_tracking
    },
    'odsledz': {
        "description": "",
        "method": steam_market.stop_market_tracking
    },
    'numerki': {
        "description": "",
        "method": lucky_numbers.get_lucky_numbers_embed
    },
    'num': {
        "description": "",
        "method": lucky_numbers.get_lucky_numbers_embed
    },
    'zast': {
        "description": "",
        "method": substitutions.get_substitutions_embed
    }
}
