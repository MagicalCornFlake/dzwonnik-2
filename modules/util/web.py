"""Utility functions for all web APIs."""

# Standard library imports
import requests
from time import time

# Local application imports
# from ..file_manager import log
from . import send_log
from .api.steam_market import NoSuchItemException


def get_error_message(e: Exception) -> str:
    if type(e) is InvalidResponseException:
        return f"Nastąpił błąd w połączeniu: {e.status_code}"
    if type(e) is TooManyRequestsException:
        return f"Musisz poczekać jeszcze {max_request_cooldown - e.time_since_last_request:.2f}s."
    if type(e) is NoSuchItemException:
        return f":x: Nie znaleziono przedmiotu `{e.query}`. Spróbuj ponownie i upewnij się, że nazwa się zgadza."
    else:
        raise e


class TooManyRequestsException(Exception):
    """Raised when the user tries to make more than one request per second.

    Attributes:
        time_since_last_request -- the time since the last request, in milliseconds
        message -- explanation of the error
    """
    def __init__(self, time_since_last_request: int, message="You must must wait for another {cooldown}s."):
        self.time_since_last_request = time_since_last_request
        self.message = message.format(cooldown=f"{(max_request_cooldown * 1000) - time_since_last_request:.2f}")
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


last_request_time: int = 0 
max_request_cooldown: int = 3  # Must wait 3s since last request


def make_request(url: str, ignore_max_requests_cooldown: bool = False) -> requests.Response:
    """Make a web request.

    Arguments:
        url -- the url of the resource to request data from

    Raises:
        TooManyRequestsException if there was more than one request made per 3 seconds
        InvalidResponseException if the request timed out or if it returned an invalid response
    """
    global last_request_time
    current_time = time()
    if current_time - last_request_time < max_request_cooldown and not ignore_max_requests_cooldown:
        raise TooManyRequestsException(int(current_time * 1000 - last_request_time * 1000))
    last_request_time = current_time
    try:
        response = requests.get(url, timeout=10)  # Waits 10s for response
    except requests.exceptions.ReadTimeout:
        raise InvalidResponseException(408)
    if response.status_code not in [requests.codes.ok, 500]:
        raise InvalidResponseException(response.status_code)
    return response


def get_html(url: str, ignore_max_requests_cooldown: bool) -> str:
    send_log(f"Fetching content from {url} ...")
    html = make_request(url, ignore_max_requests_cooldown).content.decode('UTF-8')
    return html.replace("<html><head>", "<html>\n<head>", 1) 
