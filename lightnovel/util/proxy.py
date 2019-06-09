import json
import logging
import os
from abc import ABC
from typing import List, Dict

import requests
from urllib3.util.url import parse_url

import lightnovel.util.text as textutil


class Proxy(ABC):

    def __init__(self):
        self.log = logging.getLogger(self.__class__.__name__)
        self._load()

    def _load(self):
        raise NotImplementedError('Must be overwritten')

    def request(self, method: str, url: str, **kwargs) -> requests.Response:
        self.log.debug(f"\033[36m{method}\033[0m {url}")
        left_alignment = ' ' * len(method)
        if kwargs:
            self.log.debug(f"{left_alignment}→{kwargs}")
        response: requests.Response = self._request(method, url, **kwargs)
        if response.status_code >= 500:
            color = 31  # Red
        elif response.status_code >= 400:
            color = 35  # Magenta
        elif response.status_code >= 300:
            color = 27  # Reverse
        elif response.status_code >= 200:
            color = 32  # Green
        elif response.status_code >= 100:
            color = 39  # Default
        else:
            raise Exception("Couldn't interpret response code")
        content_type = response.headers['content-type'] if 'content-type' in response.headers else '-'
        self.log.debug(f"{left_alignment} \033[{color}m← {response.status_code}\033[0m {content_type}")
        return response

    def _request(self, method: str, url: str, **kwargs) -> requests.Response:
        raise NotImplementedError('Must be overwritten')


class DirectProxy(Proxy):
    def _load(self):
        pass

    def _request(self, method: str, url: str, **kwargs) -> requests.Response:
        return requests.request(method, url, **kwargs)


class LocalProxy(Proxy, ABC):
    path = ''

    def __init__(self, path: str):
        self.path = path
        super().__init__()


class ResponseMock(requests.Response):
    def __init__(self, url: str, text: str, headers=None, status_code=200, cookies=None):
        super().__init__()
        if headers is None:
            headers = {'content-type': '-'}
        if cookies is None:
            cookies = []
        self.url = url
        self._text = text
        self._content = text.encode('utf-8')
        self.headers = headers
        self.status_code = status_code
        self.cookies = cookies

    @property
    def text(self):
        return self._text

    @property
    def content(self):
        return self._content

    def json(self):
        return json.loads(self.content)

    def raise_for_status(self):
        pass


class HtmlCachingProxy(LocalProxy):
    def _load(self):
        if not os.path.exists(self.path):
            os.makedirs(self.path)
        elif not os.path.isdir(self.path):
            self.log.warning(f"Path {self.path} is not a directory")
            return False
        return True

    def _request(self, method: str, url: str, **kwargs) -> requests.Response:
        parsed = parse_url(url)
        filepath = os.path.join(self.path, textutil.slugify(parsed.path.replace('/', '_')) + ".html")
        if os.path.exists(filepath):
            self.log.debug("Cache hit")
            with open(filepath, 'r') as fp:
                doc = fp.read()
            response = ResponseMock(url, doc)
        else:
            response = requests.request(method, url, **kwargs)
            if 'content-type' in response.headers and response.headers['content-type'].startswith('text/html'):
                with open(filepath, 'w') as fp:
                    fp.write(response.content.decode('utf-8'))
                self.log.debug("Cached answer")
        return response


class HarProxy(LocalProxy):
    har: List[Dict] = None

    def _load(self):
        try:
            with open(self.path, 'r') as fp:
                self.har = json.load(fp)
        except Exception as e:
            self.log.error(e)
            return False
        return True

    def _request(self, method: str, url: str, **kwargs) -> requests.Response:
        for entry in self.har:
            if entry['request']['method'] == method and entry['request']['url'] == url:
                return ResponseMock(
                    url,
                    entry['response']['content']['text'],
                    entry['response']['headers'],
                    entry['response']['status'],
                    entry['response']['cookies']
                )
        raise LookupError("No entry found")


class HtmlProxy(LocalProxy):
    def _load(self):
        pass

    def _request(self, method: str, url: str, **kwargs) -> requests.Response:
        if not method == "GET":
            raise LookupError(f"No entry found for {method} {url}: {method} method not supported")
        parsed = parse_url(url)
        filepath = os.path.join(self.path, textutil.slugify(parsed.path.replace('/', '_')) + ".html")
        if not os.path.isfile(filepath):
            raise LookupError(f"No entry found for {method} {url}")
        with open(filepath, 'r', encoding='utf-8') as fp:
            text = fp.read()
        return ResponseMock(url, text)
