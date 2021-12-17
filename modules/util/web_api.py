"""Utility methods for all web APIs."""
import requests
import time


class TooManyRequestsException(Exception):
    """Raised when the user tries to make more than one request per second.

    Attributes:
        time_since_last_request -- the time since the last request, in milliseconds
        message -- explanation of the error
    """
    def __init__(self, time_since_last_request: int, message="You must must wait for another {cooldown}ms."):
        self.time_since_last_request = time_since_last_request
        self.message = message.format(cooldown=f"{1000-time_since_last_request}")
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
max_request_cooldown: int = 1  # Must wait 1s since last request


def make_request(url: str) -> requests.Response:
    """Make a web request.

    Arguments:
        url -- the url of the resource to request data from

    Raises:
        TooManyRequestsException if there was more than one request made per second
        InvalidResponseException if the request timed out or if it returned an invalid response
    """
    global last_request_time
    current_time = time.time()
    if current_time - last_request_time < max_request_cooldown:
        raise TooManyRequestsException(int(current_time * 1000 - last_request_time * 1000))
    last_request_time = current_time
    try:
        response = requests.get(url, timeout=10)  # Waits 10s for response
    except requests.exceptions.ReadTimeout:
        raise InvalidResponseException(408)
    if response.status_code not in [requests.codes.ok, 500]:
        raise InvalidResponseException(response.status_code)
    return response
