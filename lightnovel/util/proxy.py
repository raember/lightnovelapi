import json
import logging
import os
from typing import List, Dict

import requests
from urllib3.util.url import parse_url, Url


class Proxy:
    path = ''
    hit = False
    EXTENSIONS = ['.html', '.jpg', '.jpeg', '.png', '.css', '.js']

    def __init__(self, path: str = '.cache'):
        self.log = logging.getLogger(self.__class__.__name__)
        self.path = path
        self._load()

    def _load(self):
        if not os.path.exists(self.path):
            os.makedirs(self.path)  # Don't use exists_ok=True; Might have '..' in path (see tests)

    def request(self, method: str, url: str, **kwargs) -> requests.Response:
        """Constructs and sends a :class:`Request <Request>`.

        :param method: method for the new :class:`Request` object.
        :param url: URL for the new :class:`Request` object.
        :param cache: (optional) Bool to disable cache
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
        cache = True
        if 'cache' in kwargs:
            cache = bool(kwargs['cache'])
            del kwargs['cache']
        response: requests.Response = self._request(method, url, cache, **kwargs)
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

    def _request(self, method: str, url: str, cache: bool = True, **kwargs) -> requests.Response:
        url_parsed = parse_url(url)
        filepath = self._get_filename(url_parsed, **kwargs)
        if cache:
            self.log.debug(f"Looking for cached request at '{filepath}'")
            if os.path.exists(filepath):
                self.log.debug(f"Cache hit")
                self.hit = True
                return self._hit(filepath, method, url_parsed, **kwargs)
            else:
                self.log.debug("Cache miss")
        self.hit = False
        return self._miss(filepath, method, url_parsed, **kwargs)

    def _get_filename(self, url: Url, **kwargs):
        path = os.path.splitext(url.path)[0] + self._extract_extension(url, **kwargs)
        return os.path.normpath(os.path.join(self.path, url.host + path))

    def _extract_extension(self, url: Url, **kwargs) -> str:
        if url.query is not None:
            self.log.warning(f"Url has query ({url.query}), which gets ignored when looking in cache.")
        url_ext = os.path.splitext(url.path)[-1]
        if url_ext == '':
            self.log.debug(f"No extension found in url path ({url.path}).")
            if 'headers' in kwargs and 'Accept' in kwargs['headers']:
                accept = kwargs['headers']['Accept']
                for ext in self.EXTENSIONS:
                    if ext[1:] in accept:
                        self.log.debug(f"Found extension '{ext[1:]}' in Accept header ({accept}).")
                        return ext
            else:
                self.log.debug("No accept headers present")
            url_ext = '.html'
            self.log.warning(f"No extension found using the Accept header. Assuming {url_ext[1:]}.")
            return url_ext
        if url_ext in self.EXTENSIONS:
            return url_ext
        self.log.error(f"None of the supported extensions matched '{url_ext}'.")
        return url_ext

    def _miss(self, filepath: str, method: str, url: Url, **kwargs) -> requests.Response:
        response = requests.request(method, url, **kwargs)
        directories = os.path.split(filepath)[0]
        if not os.path.exists(directories):
            os.makedirs(directories)  # Don't use exists_ok=True; Might have '..' in path
        with open(filepath, 'wb') as fp:
            fp.write(response.content)
        self.log.debug(f"Cached answer in '{filepath}'")
        return response

    def _hit(self, filepath: str, method: str, url: Url, **kwargs) -> requests.Response:
        with open(filepath, 'rb') as f:
            return ResponseMock(url, f.read())


class DirectProxy(Proxy):
    def _load(self):
        pass

    def _request(self, method: str, url: str, cache: bool = True, **kwargs) -> requests.Response:
        return super()._request(method, url, False, **kwargs)


class ResponseMock(requests.Response):
    def __init__(self, url: str, content: bytes, headers=None, status_code=200, cookies=None):
        super().__init__()
        if headers is None:
            headers = {'content-type': '-'}
        if cookies is None:
            cookies = []
        self.url = url
        self._content = content
        self.headers = headers
        self.status_code = status_code
        self.cookies = cookies

    @property
    def text(self):
        return self._content.decode('utf-8')

    @property
    def content(self):
        return self._content

    def json(self):
        return json.loads(self.content)

    def raise_for_status(self):
        pass


class HarProxy(Proxy):
    har: List[Dict] = None

    def _load(self):
        try:
            with open(self.path, 'r') as fp:
                self.har = json.load(fp)
        except Exception as e:
            self.log.error(e)
            return False
        return True

    def _request(self, method: str, url: str, cache: bool = True, **kwargs) -> requests.Response:
        if not cache:
            self.log.warning("Cache disable mark ignored.")
        self.log.debug(f"Looking for cached {method} request for '{url}' in har file.")
        for entry in self.har:
            if entry['request']['method'] == method and entry['request']['url'] == url:
                self.log.debug(f"Cache hit")
                self.hit = True
                return self._hit(entry, url, **kwargs)
        self.log.debug("Cache miss")
        self.hit = False
        return self._miss()

    def _miss(self, **kwargs) -> requests.Response:
        raise LookupError("No entry found")

    def _hit(self, entry: dict, url: str, **kwargs) -> requests.Response:
        return ResponseMock(
            url,
            entry['response']['content']['text'].encode('utf-8'),
            entry['response']['headers'],
            entry['response']['status'],
            entry['response']['cookies']
        )
