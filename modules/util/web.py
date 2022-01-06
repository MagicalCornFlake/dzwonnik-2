"""Utility functions for all web APIs."""

# Standard library imports
import importlib
import requests
import time

# Local application imports
from .api.steam_market import NoSuchItemException


def send_log(*msg, force: bool = False):
    """Function that defines the log behaviour when the 'bot' module has not been imported to the namespace.
    Function `enable_circular_reference` redefines this function as the 'send_log' function of the 'bot' module."""
    if not force:
        return
    print(*msg)

# The 'bot' module imports this module first, by which time the lower-defined TooManyRequestsException class has been initialised.
# This allows this module to later import functionality from the 'bot' module.
# However, if this module is imported outside of the 'bot' module, it tries to import that module, which causes an error.
# This is because, as mentioned above, the 'bot' module tries to access TooManyRequestsException which has not been initialised yet.
# For this reason, circular references are disabled by default, and can only be enabled by calling this function (from the 'bot' module).


def enable_circular_reference():
    from .. import bot
    global send_log
    send_log = bot.send_log


last_request_time: int = 0

MAX_REQUEST_COOLDOWN: int = 3  # Must wait 3s since last request


def get_error_message(ex: Exception) -> str:
    if isinstance(ex, InvalidResponseException):
        return f"Nastąpił błąd w połączeniu: {ex.status_code}"
    if isinstance(ex, TooManyRequestsException):
        return f"Musisz poczekać jeszcze {MAX_REQUEST_COOLDOWN - ex.time_since_last_request:.2f}s."
    if isinstance(ex, NoSuchItemException):
        return f":x: Nie znaleziono przedmiotu `{ex.query}`. Spróbuj ponownie i upewnij się, że nazwa się zgadza."
    else:
        raise ex


class TooManyRequestsException(Exception):
    """Raised when the user tries to make more than one request per second.

    Attributes:
        time_since_last_request -- the time since the last request, in milliseconds
        message -- explanation of the error
    """

    def __init__(self, time_since_last_request: int, message="You must must wait for another {cooldown}s."):
        self.time_since_last_request = time_since_last_request
        self.message = message.format(
            cooldown=f"{(MAX_REQUEST_COOLDOWN * 1000) - time_since_last_request:.2f}")
        super().__init__(self.message)


class InvalidResponseException(Exception):
    """Raised when the request returns with an invalid status code.

    Attributes:
        status_code -- the response status code
        message -- explanation of the error
    """

    def __init__(self, status_code: int, message="Invalid web response! Status code: {status_code}."):
        self.status_code = status_code
        self.message = message.format(status_code=status_code)
        super().__init__(self.message)


def make_request(url: str, ignore_request_limit: bool = False) -> requests.Response:
    """Make a web request.

    Arguments:
        url -- the url of the resource to request data from

    Raises:
        TooManyRequestsException if there was more than one request made per 3 seconds
        InvalidResponseException if the request timed out or if it returned an invalid response
    """
    global last_request_time
    current_time = time.time()
    if current_time - last_request_time < MAX_REQUEST_COOLDOWN and not ignore_request_limit:
        raise TooManyRequestsException(
            int(current_time * 1000 - last_request_time * 1000))
    last_request_time = current_time
    send_log(f"Fetching content from {url} ...", force=True)
    try:
        response = requests.get(url, timeout=10)  # Waits 10s for response
    except requests.exceptions.ReadTimeout:
        raise InvalidResponseException(408)
    if not 200 <= response.status_code < 300:
        raise InvalidResponseException(response.status_code)
    return response


def get_html(url: str, ignore_max_requests_cooldown: bool) -> str:
    res = make_request(url, ignore_max_requests_cooldown)
    html = res.content.decode('UTF-8')
    return html.replace("<html><head>", "<html>\n<head>", 1)
