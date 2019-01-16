import json
import logging
import os
from typing import List, Dict
from urllib3.util.url import parse_url
from util import slugify

import requests


def request(method: str, url: str, **kwargs) -> requests.Response:
    return requests.request(method, url, **kwargs)


def ipinfo():
    return request('GET', 'https://ipinfo.io/json').json()


class Proxy:
    path = ''

    def __init__(self, path):
        self.log = logging.getLogger(self.__class__.__name__)
        self.path = path

    def load(self, path: str = '') -> bool:
        if path == '':
            path = self.path
        else:
            self.path = path
        return self._load(path)

    def _load(self, path: str) -> bool:
        raise NotImplementedError('Must be overwritten')


class ResponseMock:
    def __init__(self, url: str, text: str, status_code=200, cookies=[]):
        if cookies is None:
            cookies = []
        self.url = url
        self.text = text
        self.content = text.encode('utf-8')
        self.status_code = status_code
        self.cookies = cookies

    def json(self):
        return json.loads(self.content)

    def raise_for_status(self):
        pass


class HarProxy(Proxy):
    har: List[Dict] = None

    def _load(self, path: str) -> bool:
        try:
            with open(self.path, 'r') as fp:
                self.har = json.load(fp)
        except:
            return False
        return True

    def request(self, method: str, url: str) -> requests.Response:
        self.log.info("Received {} request to {}".format(method, url))
        for entry in self.har:
            if entry['request']['method'] == method and entry['request']['url'] == url:
                return ResponseMock(
                    url,
                    entry['response']['content']['text'],
                    entry['response']['status'],
                    entry['response']['cookies']
                )
        raise LookupError("No entry found")


class HtmlProxy(Proxy):

    def _load(self, path: str) -> bool:
        return os.path.isdir(path)

    def request(self, method: str, url: str) -> requests.Response:
        self.log.info("Received {} request to {}".format(method, url))
        if not method == "GET":
            raise LookupError("No entry found")
        parsed = parse_url(url)
        if len(parsed.path.split('/')) == 2:
            filepath = os.path.join(self.path, 'index.html')
        else:
            filepath = os.path.join(self.path, slugify(parsed.path.replace('/', '_')) + ".html")
        self.log.warning(parsed.path)
        self.log.warning(slugify(parsed.path.replace('/', '_')) + ".html")
        self.log.warning(filepath)
        if not os.path.isfile(filepath):
            raise LookupError("No entry found")
        with open(filepath, 'r') as fp:
            text = fp.read()
        return ResponseMock(url, text)
