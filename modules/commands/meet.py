"""Module containing code relating to the 'meet' command."""

# Standard library imports
import re

# Third-party imports
from discord import Message

# Local application imports
from . import ensure_sender_is_admin
from .. import bot, util, file_manager, Emoji


DESC = None

LINK_PATTERN = re.compile(r"[a-z]{3}-[a-z]{4}-[a-z]{3}$|lookup/[a-z]{10}$")


class InvalidFormatException(Exception):
    """Raised when the user-inputted Google Meet link is of invalid format."""

    def __init__(self, link):
        self.message = "Invalid Googe Meet link: " + link
        super().__init__(self.message)


def update_meet_link(message: Message) -> tuple[bool, str]:
    """Event handler for the 'meet' command."""
    args = message.content.split(" ")[1:]
    try:
        if not args:
            # Display codes list if there are no arguments specified
            raise ValueError
        if args[0] not in util.lesson_links:
            # Display codes list if the code is invalid
            raise ValueError
        lesson_name = util.get_lesson_name(args[0])
        link = util.get_lesson_link(args[0])
        if len(args) == 1:
            link_desc = f"to <https://meet.google.com/{link}>" if link else "nie jest ustawiony"
            return f"{Emoji.INFO} Link do Meeta dla lekcji '__{lesson_name}__' {link_desc}."
        else:
            ensure_sender_is_admin(message, "zmieniania linków Google Meet")
            if not re.match(LINK_PATTERN, args[1]):
                # Display codes list if the specified link is of invalid format
                raise InvalidFormatException(args[1])
            # User-given link is valid
            util.lesson_links[args[0]] = args[1]
            file_manager.save_data_file()
            return (f"{Emoji.CHECK} Zmieniono link dla lekcji '__{lesson_name}__'"
                    f" z `{link}` na **{args[1]}**.")
    except InvalidFormatException:
        # noinspection SpellCheckingInspection
        invalid_format_msg = (f":warning: Uwaga: link do Meeta powinien mieć formę `xxx-xxxx-xxx`"
                              f" bądź `lookup/xxxxxxxxxx`.\n"
                              f"Argument '__{args[1]}__' nie spełnia tego wymogu.")
        return invalid_format_msg
    except ValueError:
        msg = f"Należy napisać po komendzie `{bot.prefix}meet` kod lekcji, " + \
            "aby zobaczyć jaki jest ustawiony link do Meeta dla tej lekcji, " + \
            "albo dopisać po kodzie też nowy link aby go zaktualizować.\nKody lekcji:```md"
        for lesson_code, link in util.lesson_links.items():
            msg += f"\n# {lesson_code} [{util.get_lesson_name(lesson_code)}]({link or 'brak'})"
        return msg + "```"
