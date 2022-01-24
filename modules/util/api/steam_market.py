"""Functionality for accessing the Steam Community web API."""

# Standard library imports
from urllib import parse

# Third-party imports
from corny_commons.util import web

# Local application imports
from ... import bot


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
SOURCE_URL = "{}priceoverview/?appid={}&currency={}&market_hash_name={}"


def get_currency_id(currency: str):
    """Returns the ID of a given currency if it's listed, otherwise return the ID for PLN (6)."""
    return (CURRENCY_IDS.index(currency) + 1) if currency in CURRENCY_IDS else 6


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


# Data JSON structure:
# {
#     "success": bool,
#     "lowest_price": "0,00curr",
#     "volume": "00,000",
#     "median_price": "0,00curr"
# }

def get_item(raw_query: str, app_id: int = 730, currency: str = 'PLN', force: bool = False
             ) -> dict[str, bool or str]:
    """Makes a web query on the Steam Community Market API for the specified search term.

    Arguments:
        raw_query -- the string that is to be searched for on the API.
        app_id -- the ID of the game whose market contains the searched item (default 730 - CS:GO).
        currency -- the ISO abbreviation for the currency that the results are to be returned in
        (defaults to PLN for Polish Złotys).

    Returns a dictionary containing the JSON response.
    Raises NoSuchItemException if the item was not found.
    """
    steam_url = "https://www.steamcommunity.com/market/"
    currency_id = get_currency_id(currency)
    query_encoded = parse.quote(raw_query)
    url = SOURCE_URL.format(steam_url, app_id, currency_id, query_encoded)
    result = web.make_request(url, ignore_request_limit=force).json()
    if not result["success"]:
        raise NoSuchItemException(raw_query)
    return result


def get_item_price(item_data: dict[str, bool or str]) -> str:
    """Returns the item's lowest price. If that's not available, sends the median price."""
    try:
        price = item_data['lowest_price']
    except KeyError:
        bot.send_log(f"{COULD_NOT_FIND_PRICE_MSG}\n{item_data}")
        price = item_data['median_price']
    return price
