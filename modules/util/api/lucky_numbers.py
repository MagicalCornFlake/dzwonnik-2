"""Functionality for getting the lucky numbers from the SU ILO website."""

# Standard library imports
from datetime import datetime

# Local application imports
from .. import web

# Data JSON structure:
# {
#     "date": "dd/mm/YYYY",
#     "luckyNumbers": [0, 0],
#     "excludedClasses": ["X", "Y"]
# }

cached_data: dict[str, str or list[int or str]] = {}
max_cache_age = 1  # Days


def get_lucky_numbers() -> dict[str, str or list[int or str]]:
    """Updates the cache if it is outdated then returns it."""
    current_date = datetime.now()
    try:
        last_cache_date = datetime.strptime(cached_data['date'], "%d/%m/%Y")
        if (current_date - last_cache_date).days > max_cache_age:
            raise ValueError()
    except (KeyError, ValueError):
        # If the cache is empty or too old
        update_cache()
    return cached_data


def update_cache() -> dict[str, str or list[int or str]] or bool:
    """Updates the cache with current data from the SU ILO website.
    
    Returns the old cache so that it can be compared with the new one.
    """
    url = "https://europe-west1-lucky-numbers-suilo.cloudfunctions.net/app/api/luckyNumbers"
    global cached_data
    old_cache = cached_data
    cached_data = web.make_request(url, ignore_max_requests_cooldown=True).json()
    return old_cache
