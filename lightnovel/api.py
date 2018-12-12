import requests
from .log_class import LogBase


def request(method: str, url: str, **kwargs) -> requests.Response:
    return requests.request(method, url, **kwargs)


def ipinfo():
    return request('GET', 'https://ipinfo.io/json').json()


class LightNovelApi(LogBase):
    def __init__(self, request_method=request):
        super().__init__()
        self._request = request_method
