"""Module containing code relating to the Steam Community Market commands."""

# Third-party imports
from discord import Message

# Local application imports
from . import TrackedItem, tracked_market_items
from .. import prefix, Emoji
from ..util.web_api import get_error_message
from ..util.api import steam_api
from ..file_manager import save_data_file

# Returns the message to send when the user asks for the price of an item on the Steam Community Market
def get_market_price(message: Message, result_override=None) -> tuple[bool, str]:
    args: list[str] = message.content[len(f"{prefix}cena "):].split(" waluta=") if result_override is None else [message]
    currency = args[-1] if len(args) > 1 else 'PLN'
    try:
        result = steam_api.get_item(args[0], 730, currency) if result_override is None else result_override
        return False, f"{Emoji.info} Aktualna cena dla *{args[0]}* to `{steam_api.get_item_price(result)}`."
    except Exception as e:
        return False, get_error_message(e)


# Returns the message to send when the user wishes to track an item on the Steam Community Market
def start_market_tracking(message: Message):
    # noinspection SpellCheckingInspection
    args = message.content.lstrip(f"{prefix}sledz ").split(" min=")
    min_price = args[-1].split(" max=")[0].strip()
    max_price = args[-1].split(" max=")[-1].strip()
    try:
        min_price = int(float(min_price) * 100)
        max_price = int(float(max_price) * 100)
    except ValueError:
        # noinspection SpellCheckingInspection
        return False, f"{Emoji.warning} Należy wpisać po nazwie przedmiotu cenę minimalną oraz cenę maksymalną. " \
                      f"Przykład: `{prefix}sledz Operation Broken Fang Case min=1 max=3`."
    else:
        item_name = args[0].rstrip()
        try:
            result = steam_api.get_item(item_name)
        except Exception as e:
            return False, get_error_message(e)
        else:
            author_id = message.author.id
            item = TrackedItem(item_name, min_price, max_price, author_id)
            if item in tracked_market_items:
                for item in tracked_market_items:
                    if item.name.lower() == item_name.lower():
                        return False, f"{Emoji.warning} Przedmiot *{item.name}* jest już śledzony przez " + \
                               (f"użytkownika <@{item.author_id}>." if item.author_id != author_id else "Ciebie.")
            tracked_market_items.append(item)
            save_data_file()
            return False, f"{Emoji.check} Stworzono zlecenie śledzenia przedmiotu *{item_name}* w przedziale " \
                          f"`{min_price/100:.2f}zł - {max_price/100:.2f}zł`.\n" + \
                get_market_price(item_name, result_override=result)[1]


def stop_market_tracking(message: Message) -> tuple[bool, str]:
    # noinspection SpellCheckingInspection
    item_name = message.content.lstrip(f"{prefix}odsledz ")
    for item in tracked_market_items:
        if item.name.lower() == item_name.lower():
            if item.author_id == message.author.id or message.channel.permissions_for(message.author).administrator:
                tracked_market_items.remove(item)
                save_data_file()
                return False, f"{Emoji.check} Zaprzestano śledzenie przedmiotu *{item.name}*."
            return False, f":x: Nie jesteś osobą, która zażyczyła śledzenia tego przedmiotu."
    return False, f":x: Przedmiot *{item_name}* nie jest aktualnie śledziony."
