"""Module containing code relating to the 'meet' command."""

# Third-party imports
from discord import Message

# Local application imports
from .. import bot, Emoji, util
from ..file_manager import save_data_file


desc = None


def update_meet_link(message: Message) -> tuple[bool, str]:
    args = message.content.split(" ")
    if len(args) > 1:
        lesson_name = util.get_lesson_name(args[1])
        link = util.get_lesson_link(args[1])
        if len(args) == 2:
            link_desc = f"to <https://meet.google.com/{link}?authuser=0>" if link else "nie jest ustawiony"
            return False, f"{Emoji.info} Link do Meeta dla lekcji '__{lesson_name}__' {link_desc}."
        else:
            if not message.channel.permissions_for(message.author).administrator:
                return False, f"{Emoji.warning} Nie posiadasz uprawnień do zmieniania linków Google Meet."
            link_is_dash_format = len(args[2]) == 12 and args[2][3] == args[2][8] == "-"
            link_is_lookup_format = len(args[2]) == 17 and args[2].startswith("lookup/")
            if link_is_dash_format or link_is_lookup_format:
                # User-given link is valid
                util.lesson_links[args[1]] = args[2]
                save_data_file()
                return False, f"{Emoji.check} Zmieniono link dla lekcji " \
                                f"'__{lesson_name}__' z `{link}` na **{args[2]}**."
    msg = f"Należy napisać po komendzie `{bot.prefix}meet` kod lekcji, " + \
        "aby zobaczyć jaki jest ustawiony link do Meeta dla tej lekcji, " + \
        "albo dopisać po kodzie też nowy link aby go zaktualizować.\nKody lekcji:```md"
    for lesson_code, link in util.lesson_links.items():
        msg += f"\n# {lesson_code} [{util.get_lesson_name(lesson_code)}]({link or 'brak'})"
    # noinspection SpellCheckingInspection
    msg += "```\n:warning: Uwaga: link do Meeta powinien mieć formę `xxx-xxxx-xxx` bądź `lookup/xxxxxxxxxx`."
    return False, msg
