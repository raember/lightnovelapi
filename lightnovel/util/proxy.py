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
        """Constructs and sends a :class:`Request <Request>`.

        :param method: method for the new :class:`Request` object.
        :param url: URL for the new :class:`Request` object.
        :param params: (optional) Dictionary, list of tuples or bytes to send
            in the body of the :class:`Request`.
        :param data: (optional) Dictionary, list of tuples, bytes, or file-like
            object to send in the body of the :class:`Request`.
        :param json: (optional) A JSON serializable Python object to send in the body of the :class:`Request`.
        :param headers: (optional) Dictionary of HTTP Headers to send with the :class:`Request`.
        :param cookies: (optional) Dict or CookieJar object to send with the :class:`Request`.
        :param files: (optional) Dictionary of ``'name': file-like-objects`` (or ``{'name': file-tuple}``) for multipart encoding upload.
            ``file-tuple`` can be a 2-tuple ``('filename', fileobj)``, 3-tuple ``('filename', fileobj, 'content_type')``
            or a 4-tuple ``('filename', fileobj, 'content_type', custom_headers)``, where ``'content-type'`` is a string
            defining the content type of the given file and ``custom_headers`` a dict-like object containing additional headers
            to add for the file.
        :param auth: (optional) Auth tuple to enable Basic/Digest/Custom HTTP Auth.
        :param timeout: (optional) How many seconds to wait for the server to send data
            before giving up, as a float, or a :ref:`(connect timeout, read
            timeout) <timeouts>` tuple.
        :type timeout: float or tuple
        :param allow_redirects: (optional) Boolean. Enable/disable GET/OPTIONS/POST/PUT/PATCH/DELETE/HEAD redirection. Defaults to ``True``.
        :type allow_redirects: bool
        :param proxies: (optional) Dictionary mapping protocol to the URL of the proxy.
        :param verify: (optional) Either a boolean, in which case it controls whether we verify
                the server's TLS certificate, or a string, in which case it must be a path
                to a CA bundle to use. Defaults to ``True``.
        :param stream: (optional) if ``False``, the response content will be immediately downloaded.
        :param cert: (optional) if String, path to ssl client cert file (.pem). If Tuple, ('cert', 'key') pair.
        :return: :class:`Response <Response>` object
        :rtype: requests.Response

        Usage::

          >>> import requests
          >>> req = requests.request('GET', 'https://httpbin.org/get')
          <Response [200]>
        """
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
