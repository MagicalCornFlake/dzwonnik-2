"""Functionality for getting the lucky numbers from the SU ILO website"""
from . import web_api


cached_data = {}


def get_lucky_numbers():
    url = "https://europe-west1-lucky-numbers-suilo.cloudfunctions.net/app/api/luckyNumbers"
    # JSON structure:
    # {
    #     "date": "dd/mm/YYYY",
    #     "luckyNumbers": [0, 0],
    #     "excludedClasses": ["X", "Y"]
    # }
    return web_api.make_request(url)
