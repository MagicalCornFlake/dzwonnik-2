"""Functionality for scraping the data from lo1.gliwice.pl website to retrieve lesson substitution details."""
import re

# If this script is run manually, it must be done so from a root package with the -m flag. For example:
# ... dzwonnik-2/modules $ python -m util.crawlers.plan_crawler
from .. api import web_api
