"""Functionality for scraping the data from lo1.gliwice.pl website to retrieve lesson substitution details"""
import importlib
import re

if __name__ == "__main__":
    from ..api import web_api
else:
    web_api = importlib.import_module('modules.util.api.web_api')

