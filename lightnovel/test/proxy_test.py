import os.path
import unittest
from unittest.mock import patch

from urllib3.util import Url

from test.test_config import CACHEFOLDER, Hars
from util import Proxy, DirectProxy, HarProxy
from util.proxy import ResponseMock


def request(method, url, **kwargs):
    return ResponseMock('url', b'str')


def miss_mock(filepath: str, method: str, url: Url, **kwargs):
    return ResponseMock('url', b'str')


class DirectProxyTest(unittest.TestCase):
    @patch("requests.request", side_effect=request)
    def test_request(self, _):
        proxy = DirectProxy()
        resp = proxy.request('GET', 'https://ipinfo.io/json')
        self.assertIsNotNone(resp)
        self.assertEqual('url', resp.url)
        self.assertEqual('str', resp.text)


class CachingProxyTest(unittest.TestCase):
    def test_instantiation(self):
        proxy = Proxy(CACHEFOLDER)
        self.assertIsNotNone(proxy)

    def test_request_hit(self):
        proxy = Proxy(CACHEFOLDER)
        self.assertIsNotNone(proxy.request("GET", "https://www.wuxiaworld.com/novel/heavenly-jewel-change"))

    @patch("util.Proxy._miss", side_effect=miss_mock)
    def test_request_miss(self, _):
        proxy = Proxy(CACHEFOLDER)
        resp = proxy.request("GET", "https://www.wuxiaworld.com/novel/heavenly-jewel-change/")
        self.assertIsNotNone(resp)
        self.assertEqual('url', resp.url)
        self.assertEqual('str', resp.text)


class HarProxyTest(unittest.TestCase):
    def test_load_har(self):
        proxy = HarProxy(os.path.join(*Hars.WW_WMW_COVER_C1))
        self.assertIsNotNone(proxy)
        self.assertIsNotNone(proxy.har)

    def test_request(self):
        proxy = HarProxy(os.path.join(*Hars.WW_WMW_COVER_C1))
        self.assertIsNotNone(proxy.request("GET", "https://www.wuxiaworld.com/novel/warlock-of-the-magus-world"))

    def test_request_fail(self):
        proxy = HarProxy(os.path.join(*Hars.WW_WMW_COVER_C1))
        with self.assertRaises(LookupError):
            proxy.request("GET", "https://www.wuxiaworld.com/novel/warlock-of-the-magus-world/")
        with self.assertRaises(LookupError):
            proxy.request("GET", "http://www.wuxiaworld.com/novel/warlock-of-the-magus-world")
        with self.assertRaises(LookupError):
            proxy.request("GET", "www.wuxiaworld.com/novel/warlock-of-the-magus-world")

    def test_image_request(self):
        proxy = HarProxy(os.path.join(*Hars.WW_WMW_COVER_C1))
        self.assertIsNotNone(proxy.request("GET", "https://cdn.wuxiaworld.com/images/covers/wmw.jpg?ver"
                                                  "=2839cf223fce0da2ff6da6ae32ab0c4e705eee1a"))
