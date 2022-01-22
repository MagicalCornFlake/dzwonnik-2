"""Functionality for getting the lucky numbers from the SU ILO website."""

# Standard library imports
from datetime import date, datetime
import json

# Third-party
from corny_commons.util import web

# Data JSON structure:
# {
#     "date": "dd/mm/YYYY",
#     "luckyNumbers": [0, 0],
#     "excludedClasses": ["X", "Y"]
# }

cached_data: dict[str, date or list[int or str]] = {}

MAX_CACHE_AGE = 1  # Days
SOURCE_URL = "https://europe-west1-lucky-numbers-suilo.cloudfunctions.net/app/api/luckyNumbers"


def get_lucky_numbers() -> dict[str, str or list[int or str]]:
    """Updates the cache if it is outdated then returns it."""
    current_date: date = date.today()
    try:
        last_cache_date: date = cached_data["date"]
        if (current_date - last_cache_date).days > MAX_CACHE_AGE:
            raise ValueError()
    except (KeyError, ValueError):
        # If the cache is empty or too old
        try:
            update_cache()
        except web.InvalidResponseException:
            # Do not update the cache if new data could not be fetched
            pass
    return cached_data


def update_cache() -> dict[str, str or list[int or str]]:
    """Updates the cache with current data from the SU ILO website.

    Returns the old cache so that it can be compared with the new one.
    """
    old_cache = dict(cached_data or {})
    cached_data.clear()
    res = web.make_request(SOURCE_URL, ignore_request_limit=True)
    cached_data.update(res.json())
    # If the date string is present in the dictionary, convert it into a date object.
    if cached_data["date"]:
        data_timestamp = datetime.strptime(cached_data["date"], "%d/%m/%Y")
        cached_data["date"] = data_timestamp.date()
    return old_cache


def serialise(data: dict = None, pretty: bool = False) -> dict or str:
    """Returns the cached data as a JSON-serialisable dictionary.

    Arguments:
        data -- a dictionary to serialise. If not specified, the lucky numbers cached data is used.
        pretty -- if True, the returned value is a string representing the pretty-printed data.

    A dictionary with all values stringified using the str function, or the pretty-printed form of
    that dictionary.
    """
    temp: dict = dict(data or cached_data or {})
    for key, value in temp.items():
        try:
            json.dumps(value)
        except TypeError:
            temp[key] = str(value)
    if pretty:
        return json.dumps(temp, indent=2)
    return temp
