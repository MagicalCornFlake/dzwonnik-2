"""Functionality for scraping the data from lo1.gliwice.pl website to retrieve lesson substitution details."""
import json
import re

# Third-party imports
import lxml.html

# If this script is run manually, it must be done so from a root package with the -m flag. For example:
# ... dzwonnik-2/modules $ python -m util.crawlers.plan_crawler
from .. import web_api
from ... import file_manager
from ... constants import Colour


def parse_html(html: str) -> dict:
    """Parses the HTML and finds a specific hard-coded table, then collects the timetable data from it.

    Arguments:
        html -- a string containing whole HTML code, eg. from the contents of a web request's response.

    Returns a dictionary.
    """
    root = lxml.html.fromstring(html)
    content = root.get_element_by_id("content")
    sidebar = root.get_element_by_id("sidebar")
    return { "content": dict(content.attrib), "sidebar": dict(sidebar.attrib) }


def get_substitutions(force_update: bool = False) -> tuple[dict, bool]:
    """Gets the current lesson substitutions.
    Returns the data itself and a tuple containing a boolean indicating if the cache already existed.

    Arguments:
        force_update -- a boolean indicating if the cache should be forcefully updated.
    """
    update_cache_callback: function = lambda force: parse_html(web_api.get_html("http://www.lo1.gliwice.pl/zastepstwa-2/", force))
    return file_manager.get_cache("subs", force_update, update_cache_callback)


if __name__ == "__main__":
    colours = vars(Colour)
    for col in colours:
        if not col.startswith('_') and col is not None:
            print(f"Colour {colours[col]}{col}{Colour.ENDC}")
    print()
    try:
        plan = json.dumps(get_substitutions(), indent=4, ensure_ascii=False)
        print(f"{Colour.OKGREEN}Substitutions:\n{Colour.ENDC}{plan}")
    except KeyboardInterrupt:
        print(f"...{Colour.FAIL}\nGoodbye!\n{Colour.ENDC}")
