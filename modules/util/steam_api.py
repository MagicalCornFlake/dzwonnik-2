"""
Functionality for accessing the Steam Community web API
"""
import requests
import time
import urllib.parse
from . import web_api


class SearchResult:
    def __init__(self, success, lowest_price, volume, median_price):
        self.success = success
        self.lowest_price = lowest_price
        self.volume = volume
        self.median_price = median_price


currency_ids = [
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


def get_currency_id(currency: str):
    # If the given currency name (e.g. EUR) is in the list of currencies, return its index otherwise return 6 (PLN)
    return (currency_ids.index(currency) + 1) if currency in currency_ids else 6


# Define custom exceptions
class NoSuchItemException(Exception):
    """
    Raised when there is no item with the given name on the Steam Community Market

    Attributes:
        query -- the item that was searched for
        message -- explanation of the error
    """

    def __init__(self, query: str, message="There is no item called '{query}' on the Steam Community Market."):
        self.query = query
        self.message = message.format(query=query)
        super().__init__(self.message)


def get_item(raw_query: str, app_id: int = 730, currency: str = 'PLN'):
    steam_url = "https://www.steamcommunity.com/market/"
    currency_id = get_currency_id(currency)
    query_encoded = urllib.parse.quote(raw_query)
    # noinspection SpellCheckingInspection
    url = f"{steam_url}priceoverview/?appid={app_id}&currency={currency_id}&market_hash_name={query_encoded}"
    result = web_api.make_request(url)
    if not result["success"]:
        raise NoSuchItemException(raw_query)
    return result


def get_item_price(item_data: dict):
    try:
        price = item_data['lowest_price']
    except KeyError:
        print(f"Could not find item's lowest price. Check if this is true:\n{item_data}")
        price = item_data['median_price']
    return price

