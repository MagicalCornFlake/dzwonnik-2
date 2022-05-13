"""Functionality for accessing the Steam Community web API."""

# Standard library imports
import json
from urllib import parse

# Third-party imports
from corny_commons.util import web

# Local application imports
from modules import bot


CURRENCY_IDS = [
    'USD',  # United States Dollar
    'GBP',  # Great British Pound
    'EUR',  # Euro
    'CHF',  # Swiss Franc
    'RUB',  # Russian Ruble
    'PLN',  # Polish Zloty
    'BRL',  # Brazilian Real
    'JPY',  # Japanese Yen
    'NOK',  # Norwegian Krone
    'IDR',  # Indonesian Rupee
    'MYR',  # Malaysian Ringgit
    'PHP',  # Philippine Peso
    'SGD',  # Singapore Dollar
    'THB',  # Thai Baht
    'VND',  # Vietnamese Dong
    'KRW',  # South Korean Won
    'TRY',  # Turkish Lira
    'UAH',  # Ukrainian Hryvnia
    'MXN',  # Mexican Peso
    'CAD',  # Canadian Dollar
    'AUD',  # Australian Dollar
    'NZD',  # New Zealand Dollar
    'CNY',  # Chinese Yuan Renminbi
    'INR',  # Indian Rupee
    'CLP',  # Chilean Peso
    'PEN',  # Peruvian Sol
    'COP',  # Colombian Peso
    'ZAR',  # South African Rand
    'HKD',  # Hong Kong Dollar
    'TWD',  # Taiwan New Dollar
    'SAR',  # Saudi Arabian Riyal
    'AED'   # Emirati Dirham
]

COULD_NOT_FIND_PRICE_MSG = "Could not find item's lowest price. Check if this is true:"

SOURCE_URL_A = ("https://www.steamcommunity.com/market/priceoverview/"
              "?appid={}&currency={}&market_hash_name=")

SOURCE_URL_B = ("https://steamcommunity.com/market/search/render/"
                "?norender=1&start={}&count={}&query=")


def get_currency_id(currency: str):
    """Returns the ID of a given currency if it's listed, otherwise return the ID for PLN (6)."""
    try:
        return CURRENCY_IDS.index(currency) + 1
    except ValueError:
        return 6

# Define custom exceptions
class NoSuchItemException(web.WebException):
    """Raised when there is no item with the given name on the Steam Community Market

    Attributes:
        query -- the item that was searched for
        message -- explanation of the error
    """

    _default_message = "There is no item called '{query}' on the Steam Community Market."

    def __init__(self, query: str, message=_default_message):
        self.query = query
        self.message = message.format(query=query)
        super().__init__(self.message)


def _make_api_request(url_template, raw_query: str, force: bool) -> dict[str, any]:
    """Makes a query on the Steam API searching for market items with the given name.

    Returns a dictionary containing the JSON response.
    Raises NoSuchItemException if the item was not found.
    """
    query_encoded = parse.quote(raw_query)
    try:
        result = web.make_request(url_template + query_encoded, ignore_request_limit=force).json()
    except web.InvalidResponseException as not_found_exc:
        raise NoSuchItemException(raw_query) from not_found_exc
    else:
        if not result.get("success"):
            raise NoSuchItemException(raw_query)
    return result


def get_item(raw_query: str, app_id: int = 730, currency: str = 'PLN', force: bool = False
             ) -> dict[str, bool or str]:
    """Makes a web query on the Steam Community Market API for the specified search term.

    Arguments:
        raw_query -- the string that is to be searched for on the API.
        app_id -- the ID of the game whose market contains the searched item (default 730 - CS:GO).
        currency -- the ISO abbreviation for the currency that the results are to be returned in
        (defaults to PLN for Polish Złotys).
        force -- a boolean indicating if the request limit should be ignored. Defaults to False.

    Returns a dictionary containing the JSON response.
    Raises NoSuchItemException if the item was not found.
    """
    # Data JSON structure:
    # {
    #     "success": bool,
    #     "lowest_price"?: "0,00curr",
    #     "volume"?: "00,000",
    #     "median_price"?: "0,00curr"
    # }
    currency_id = get_currency_id(currency)
    url_template = SOURCE_URL_A.format(app_id, currency_id)
    return _make_api_request(url_template, raw_query, force)


def search_item(raw_query: str, force: bool = False) -> dict[str, any]:
    """Makes a query on the Steam API searching for market items with the given name.

    Arguments:
        raw_query -- the string that is to be searched for on the API.
        force -- a boolean indicating if the request limit should be ignored. Defaults to False.

    Returns a dictionary containing the API response.
    Raises NoSuchItemException if the item was not found.
    """
    start_index = 0
    max_results = 10
    url_template = SOURCE_URL_B.format(start_index, max_results)
    return _make_api_request(url_template, raw_query, force)


def get_item_price(item_data: dict[str, bool or str]) -> str:
    """Returns the item's lowest price. If that's not available, sends the median price."""
    try:
        price = item_data['lowest_price']
    except KeyError:
        bot.send_log(f"{COULD_NOT_FIND_PRICE_MSG}\n{item_data}", force=True)
        price = item_data['median_price']
    return price


if __name__ == "__main__":
    # Debugging mode CLI
    try:
        while True:
            search_mode = input("Enter input mode (search | item info)...\n> ").startswith("s")
            api_function, mode_text = (search_item, "search") if search_mode else (get_item, "info")
            try:
                while True:
                    usr_input = input(f"Enter query ({mode_text} mode)...\n> ")
                    try:
                        output = api_function(usr_input)
                    except web.WebException as invalid_response_exc:
                        print(">>> ERROR!", invalid_response_exc)
                    else:
                        pretty = json.dumps(output, indent=2, ensure_ascii=False)
                        print(pretty)
            except KeyboardInterrupt:
                print("\n")
    except KeyboardInterrupt:
        print("\nGoodbye!")
