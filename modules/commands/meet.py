"""Module containing code relating to the 'meet' command."""

# Standard library imports
import re

# Third-party imports
from discord import Message

# Local application imports
from .. import bot, util, file_manager, Emoji


desc = None
link_pattern = re.compile(r"[a-z]{3}-[a-z]{4}-[a-z]{3}$|lookup/[a-z]{10}$")


class InvalidFormatException(Exception):
    """Raised when the user-inputted Google Meet link is of invalid format."""

    def init(self, link):
        self.message = "Invalid Googe Meet link: " + link
        super.__init__(self.message)


def update_meet_link(message: Message) -> tuple[bool, str]:
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
            return False, f"{Emoji.info} Link do Meeta dla lekcji '__{lesson_name}__' {link_desc}."
        else:
            if not message.channel.permissions_for(message.author).administrator:
                raise bot.MissingPermissionsException
            if not (re.match(link_pattern, args[1])):
                # Display codes list if the specified link is of invalid format
                raise InvalidFormatException(args[1])
            # User-given link is valid
            util.lesson_links[args[0]] = args[1]
            file_manager.save_data_file()
            return False, f"{Emoji.check} Zmieniono link dla lekcji " \
                f"'__{lesson_name}__' z `{link}` na **{args[1]}**."
    except bot.MissingPermissionsException:
        return False, f"{Emoji.warning} Nie posiadasz uprawnień do zmieniania linków Google Meet."
    except InvalidFormatException:
        # noinspection SpellCheckingInspection
        msg_first_line = ":warning: Uwaga: link do Meeta powinien mieć formę `xxx-xxxx-xxx` bądź `lookup/xxxxxxxxxx`."
        return False, msg_first_line + f"\nArgument '__{args[1]}__' nie spełnia tego wymogu."
    except ValueError:
        msg = f"Należy napisać po komendzie `{bot.prefix}meet` kod lekcji, " + \
            "aby zobaczyć jaki jest ustawiony link do Meeta dla tej lekcji, " + \
            "albo dopisać po kodzie też nowy link aby go zaktualizować.\nKody lekcji:```md"
        for lesson_code, link in util.lesson_links.items():
            msg += f"\n# {lesson_code} [{util.get_lesson_name(lesson_code)}]({link or 'brak'})"
        return False, msg + "```"
