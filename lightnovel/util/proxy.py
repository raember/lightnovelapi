import json
import logging
import os
from typing import List, Dict
from urllib3.util.url import parse_url
import lightnovel.util.text as textutil

import requests


def ipinfo():
    return requests.request('GET', 'https://ipinfo.io/json').json()


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

    def request(self, method: str, url: str, **kwargs) -> requests.Response:
        self.log.debug("\033[36m{}\033[0m {}".format(method, url))
        if kwargs:
            self.log.debug("{}→{}".format(" " * len(method), kwargs))
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
        self.log.debug("{} \033[{}m← {}\033[0m {}".format(
            " " * len(method),
            color,
            response.status_code,
            response.headers['content-type'] if 'content-type' in response.headers else '-'
        ))
        return response

    def _request(self, method: str, url: str, **kwargs):
        raise NotImplementedError('Must be overwritten')


class DirectProxy(Proxy):
    def _load(self, path: str) -> bool:
        return True

    def _request(self, method: str, url: str, **kwargs):
        return requests.request(method, url, **kwargs)


class ResponseMock:
    def __init__(self, url: str, text: str, headers=None, status_code=200, cookies=None):
        if headers is None:
            headers = {'content-type': '-'}
        if cookies is None:
            cookies = []
        self.url = url
        self.text = text
        self.content = text.encode('utf-8')
        self.headers = headers
        self.status_code = status_code
        self.cookies = cookies

    def json(self):
        return json.loads(self.content)

    def raise_for_status(self):
        pass


class HtmlCachingProxy(Proxy):
    def _load(self, path: str) -> bool:
        if not os.path.exists(path):
            os.makedirs(path)
        elif not os.path.isdir(path):
            self.log.warning("Path {} is not a directory".format(path))
            return False
        return True

    def _request(self, method: str, url: str, **kwargs):
        parsed = parse_url(url)
        filepath = os.path.join(self.path, textutil.slugify(parsed.path.replace('/', '_')) + ".html")
        if os.path.exists(filepath):
            self.log.debug("Found response in cache")
            with open(filepath, 'r') as fp:
                doc = fp.read()
            response = ResponseMock(url, doc)
        else:
            response = requests.request(method, url, **kwargs)
            if 'content-type' in response.headers and response.headers['content-type'].startswith('text/html'):
                with open(filepath, 'w') as fp:
                    fp.write(response.content.decode('utf-8'))
        return response


class HarProxy(Proxy):
    har: List[Dict] = None

    def _load(self, path: str) -> bool:
        try:
            with open(self.path, 'r') as fp:
                self.har = json.load(fp)
        except Exception as e:
            self.log.error(e)
            return False
        return True

    def _request(self, method: str, url: str, **kwargs):
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


class HtmlProxy(Proxy):

    def _load(self, path: str) -> bool:
        # print(os.path.isdir('.'))
        # print(os.path.curdir)
        # print(os.path.isdir(os.path.curdir))
        # print(os.listdir('.'))
        # print(path)
        # print(os.path.isdir(path))
        return os.path.isdir(path)

    def _request(self, method: str, url: str, **kwargs):
        if not method == "GET":
            raise LookupError("No entry found for {} {}".format(method, url))
        parsed = parse_url(url)
        filepath = os.path.join(self.path, textutil.slugify(parsed.path.replace('/', '_')) + ".html")
        # self.log.warning(parsed.path)
        # self.log.warning(textutil.slugify(parsed.path.replace('/', '_')) + ".html")
        # self.log.warning(filepath)
        if not os.path.isfile(filepath):
            raise LookupError("No entry found for {} {}".format(method, url))
        with open(filepath, 'r') as fp:
            text = fp.read()
        return ResponseMock(url, text)
