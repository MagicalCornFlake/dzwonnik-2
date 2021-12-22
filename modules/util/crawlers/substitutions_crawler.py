"""Functionality for scraping the data from lo1.gliwice.pl website to retrieve lesson substitution details."""
from datetime import datetime
import re

# If this script is run manually, it must be done so from a root package with the -m flag. For example:
# ... dzwonnik-2/modules $ python -m util.crawlers.plan_crawler
from .. import web_api
from ... import file_management


def parse_html(html: str) -> dict:
    return {
        "date": datetime.strftime(datetime.now(), "%d.%m.%Y"),
        "html": html
    }


def get_substitutions(force_update: bool = False) -> tuple[dict, bool]:
    """Gets the current lesson substitutions.
    Returns the data itself and a tuple containing a boolean indicating if the cache needed to be updated.

    Arguments:
        force_update -- a boolean indicating if the cache should be forcefully updated.
    """
    update_cache_callback: function = lambda force: parse_html(web_api.get_html("http://www.lo1.gliwice.pl/zastepstwa-2/", force))
    cache, cache_existed = file_management.get_cache("subs", force_update, update_cache_callback)
    return cache, not cache_existed
