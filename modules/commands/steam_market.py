"""Module containing code relating to the Steam Community Market commands."""

# Third-party imports
from discord import Message, Embed
from corny_commons.util import web

# Local application imports
from modules import bot, util, data_manager, Emoji
from modules.commands import TrackedItem, ensure_user_authorised, tracked_market_items
from modules.api import steam_market


DESC = """Podaje aktualną cenę dla szukanego przedmiotu na Rynku Społeczności Steam.
Parametry: __przedmiot__, __waluta__
Przykłady: 
`{p}cena Operation Broken Fang Case` - wyświetliłaby się cena dla tego przedmiotu, domyślnie w zł.
`{p}cena Operation Broken Fang Case waluta=EUR` - wyświetliłaby się cena w euro."""
DESC_SEARCH = """Wykonuje wyszukiwanie przedmiotów w bazie danych Rynku Społeczności Steam.
Parametry: __przedmiot__
Przykład:
`{p}wyszukaj Operation Broken Fang` - wyświetliłaby się lista zawierająca do dziesięciu przedmiotów.
"""
DESC_TRACK = """Zaczyna śledzić dany przedmiot na Rynku Społeczności Steam i wysyła powiadomienie, \
gdy cena wykroczy podaną granicę.
Parametry: __nazwa przedmiotu__, __cena minimalna__, __cena maksymalna__
Przykład: `{p}sledz Operation Broken Fang Case min=1.00 max=3.00` - stworzyłoby się zlecenie śledz\
enia tego przedmiotu z powiadomieniem, gdy cena się obniży poniżej 1,00zł lub przekroczy 3,00zł."""
DESC_UNTRACK = """Przestaje śledzić dany przedmiot na Rynku Społeczności Steam.
Parametry: __nazwa przedmiotu__
Przykład: `{p}odsledz Operation Broken Fang Case` - zaprzestaje śledzenie ceny tego przedmiotu."""

STEAM_URL = "https://www.steamcommunity.com/market/search/?q="


def get_market_price(message: Message or str, result_override=None) -> str:
    """Event handler for the 'cena' command."""
    if result_override is None:
        args: list[str] = message.content[len(f"{bot.prefix}cena "):].split(" waluta=")
    else:
        args: list[str] = [message]
    currency = args[-1].strip() if len(args) > 1 else 'PLN'
    try:
        params = args[0], 730, currency
        result = result_override or steam_market.get_item(*params)
        price = steam_market.get_item_price(result)
    except web.WebException as web_exc:
        return util.get_error_message(web_exc)
    else:
        return f"{Emoji.INFO} Aktualna cena dla *{args[0]}* to `{price}`."


def search_for_item(message: Message) -> Embed:
    """Event handler for the 'wyszukaj' command."""
    raw_query = message.content[len(f"{bot.prefix}wyszukaj "):]
    try:
        response: dict[str, any] = steam_market.search_item(raw_query)
    except web.WebException as web_exc:
        return util.get_error_message(web_exc)
    total =  response.get("total_count", 0)
    first = response.get("start", -1) + 1
    last = min(response.get("pagesize", first), total)
    desc = f"Pokazuję {first}-{last} z {total}."
    url = STEAM_URL + response["query_encoded"]
    embed = Embed(title=f"Wynik wyszukania \"{raw_query}\":", description=desc, url=url)
    for result in response.get("results", []):
        game = result['app_name']
        price = result['sell_price_text']
        volume = result['sell_listings']
        text = f"Gra: {game}\nCena: {price}\nIlość: {volume}\nNazwa: {result['hash_name']}"
        embed.add_field(name=result["name"], value=text, inline=False)
    return embed


# Returns the message to send when the user wishes to track an item on the Steam Community Market
def start_market_tracking(message: Message):
    """Event handling for the 'sledz' command."""
    # noinspection SpellCheckingInspection
    args = message.content[len(f"{bot.prefix}sledz "):].split(" min=")
    min_price = args[-1].split(" max=")[0].strip()
    max_price = args[-1].split(" max=")[-1].strip()
    try:
        min_price = int(float(min_price) * 100)
        max_price = int(float(max_price) * 100)
    except ValueError:
        # noinspection SpellCheckingInspection
        return (f"{Emoji.WARNING} Należy wpisać po nazwie przedmiotu cenę minimalną oraz "
                f"cenę maksymalną. Przykład: `{bot.prefix}sledz Operation Broken Fang Case "
                f"min=1 max=3`.")
    else:
        item_name = args[0].rstrip()
        try:
            result = steam_market.get_item(item_name)
        except web.WebException as ex:
            return util.get_error_message(ex)
        else:
            author_id = message.author.id
            item = TrackedItem(item_name, min_price, max_price, author_id)
            if item in tracked_market_items:
                for item in tracked_market_items:
                    if item.name.lower() == item_name.lower():
                        author = f"użytkownika <@{item.author_id}>"
                        who = author if item.author_id != author_id else "Ciebie"
                        return (f"{Emoji.WARNING} Przedmiot *{item.name}* jest już śledzony"
                                f"przez {who}.")
            tracked_market_items.append(item)
            data_manager.save_data_file()
            price = get_market_price(item_name, result_override=result)
            return (f"{Emoji.CHECK} Stworzono zlecenie śledzenia przedmiotu *{item_name}* w"
                    f" przedziale `{min_price/100:.2f}zł - {max_price/100:.2f}zł`.\n{price}")


def stop_market_tracking(message: Message) -> str:
    """Event handling for the 'odsledz' command."""
    # noinspection SpellCheckingInspection
    item_name = message.content.lstrip(f"{bot.prefix}odsledz ")
    for item in tracked_market_items:
        if item.name.lower() == item_name.lower():
            if item.author_id != message.author.id:
                ensure_user_authorised(message, "usuwania tego zlecenia")
            tracked_market_items.remove(item)
            data_manager.save_data_file()
            return f"{Emoji.CHECK} Zaprzestano śledzenie przedmiotu *{item.name}*."
    return f":x: Przedmiot *{item_name}* nie jest aktualnie śledziony."
