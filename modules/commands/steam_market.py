"""Module containing code relating to the Steam Community Market commands."""

# Third-party imports
from discord import Message

# Local application imports
from . import TrackedItem, tracked_market_items
from .. import bot, file_manager, Emoji
from ..util import web
from ..util.api import steam_market as steam_market_api


desc = """Podaje aktualną cenę dla szukanego przedmiotu na Rynku Społeczności Steam.
    Parametry: __przedmiot__, __waluta__
    Przykłady: 
    `{p}cena Operation Broken Fang Case` - wyświetliłaby się cena dla tego przedmiotu, domyślnie w zł.
    `{p}cena Operation Broken Fang Case waluta=EUR` - wyświetliłaby się cena dla tego przedmiotu w euro."""
desc_2 = """Zaczyna śledzić dany przedmiot na Rynku Społeczności Steam \
    i wysyła powiadomienie, gdy cena wykroczy podaną granicę.
    Parametry: __nazwa przedmiotu__, __cena minimalna__, __cena maksymalna__,
    Przykład: `{p}sledz Operation Broken Fang Case min=1.00 max=3.00` - stworzyłoby się zlecenie śledzenia tego\
    przedmiotu z powiadomieniem, gdy cena się obniży poniżej 1,00zł lub przekroczy 3,00zł."""
desc_3 = """Przestaje śledzić dany przedmiot na Rynku Społeczności Steam.
    Parametry: __nazwa przedmiotu__
    Przykład: `{p}odsledz Operation Broken Fang Case` - zaprzestaje śledzenie ceny tego przedmiotu."""


def get_market_price(message: Message, result_override=None) -> tuple[bool, str]:
    """Returns the message to send when the user asks for the price of an item on the Steam Community Market"""
    raw_args = message.content[len(f"{bot.prefix}cena "):].split(" waluta=")
    args: list[str] = [message] if result_override else raw_args
    currency = args[-1] if len(args) > 1 else 'PLN'
    try:
        params = args[0], 730, currency
        result = result_override or steam_market_api.get_item(*params)
        return False, f"{Emoji.info} Aktualna cena dla *{args[0]}* to `{steam_market_api.get_item_price(result)}`."
    except Exception as e:
        return False, web.get_error_message(e)


# Returns the message to send when the user wishes to track an item on the Steam Community Market
def start_market_tracking(message: Message):
    # noinspection SpellCheckingInspection
    args = message.content.lstrip(f"{bot.prefix}sledz ").split(" min=")
    min_price = args[-1].split(" max=")[0].strip()
    max_price = args[-1].split(" max=")[-1].strip()
    try:
        min_price = int(float(min_price) * 100)
        max_price = int(float(max_price) * 100)
    except ValueError:
        # noinspection SpellCheckingInspection
        return False, f"{Emoji.warning} Należy wpisać po nazwie przedmiotu cenę minimalną oraz cenę maksymalną. " \
                      f"Przykład: `{bot.prefix}sledz Operation Broken Fang Case min=1 max=3`."
    else:
        item_name = args[0].rstrip()
        try:
            result = steam_market_api.get_item(item_name)
        except Exception as e:
            return False, web.get_error_message(e)
        else:
            author_id = message.author.id
            item = TrackedItem(item_name, min_price, max_price, author_id)
            if item in tracked_market_items:
                for item in tracked_market_items:
                    if item.name.lower() == item_name.lower():
                        who = f"użytkownika <@{item.author_id}>" if item.author_id != author_id else "Ciebie"
                        return False, f"{Emoji.warning} Przedmiot *{item.name}* jest już śledzony przez {who}."
            tracked_market_items.append(item)
            file_manager.save_data_file()
            return False, f"{Emoji.check} Stworzono zlecenie śledzenia przedmiotu *{item_name}* w przedziale " \
                          f"`{min_price/100:.2f}zł - {max_price/100:.2f}zł`.\n" + \
                get_market_price(item_name, result_override=result)[1]


def stop_market_tracking(message: Message) -> tuple[bool, str]:
    # noinspection SpellCheckingInspection
    item_name = message.content.lstrip(f"{bot.prefix}odsledz ")
    for item in tracked_market_items:
        if item.name.lower() == item_name.lower():
            if item.author_id == message.author.id or message.channel.permissions_for(message.author).administrator:
                tracked_market_items.remove(item)
                file_manager.save_data_file()
                return False, f"{Emoji.check} Zaprzestano śledzenie przedmiotu *{item.name}*."
            return False, f":x: Nie jesteś osobą, która zażyczyła śledzenia tego przedmiotu."
    return False, f":x: Przedmiot *{item_name}* nie jest aktualnie śledziony."
