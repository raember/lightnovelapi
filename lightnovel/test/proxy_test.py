import os.path
import unittest
from unittest.mock import patch, MagicMock

from urllib3.util import Url

from test.test_config import cache_folder, Har
from util import Proxy, DirectProxy, HarProxy
from util.proxy import ResponseMock


def request(method, url, **kwargs):
    return ResponseMock('url', b'str')


def miss_mock(filepath: str, method: str, url: Url, **kwargs):
    return ResponseMock('url', b'str')


def remove(filepath: str):
    pass


class DirectProxyTest(unittest.TestCase):
    @patch("requests.request", side_effect=request)
    def test_request(self, _):
        proxy = DirectProxy('../.cache')
        resp = proxy.request('GET', 'https://ipinfo.io/json')
        self.assertIsNotNone(resp)
        self.assertEqual('url', resp.url)
        self.assertEqual('str', resp.text)


class CachingProxyTest(unittest.TestCase):
    def test_instantiation(self):
        proxy = Proxy(cache_folder)
        self.assertIsNotNone(proxy)

    def test_request_hit(self):
        proxy = Proxy(cache_folder)
        self.assertIsNotNone(proxy.request("GET", "https://www.wuxiaworld.com/novel/heavenly-jewel-change"))

    @patch("util.Proxy._miss", side_effect=miss_mock)
    def test_request_miss(self, _):
        proxy = Proxy(cache_folder)
        resp = proxy.request("GET", "https://www.wuxiaworld.com/novel/heavenly-jewel-change/")
        self.assertIsNotNone(resp)
        self.assertEqual('url', resp.url)
        self.assertEqual('str', resp.text)

    @patch("os.remove", side_effect=remove)
    def test_delete_from_cache_specific(self, f_remove: MagicMock):
        proxy = Proxy(cache_folder)
        resp = proxy.request("GET", "https://httpbin.org/anything", headers={'Accept': 'text/json'})
        self.assertIsNotNone(resp)
        self.assertFalse(f_remove.called)
        proxy.delete_from_cache("https://httpbin.org/anything", headers={'Accept': 'text/json'})
        self.assertTrue(f_remove.called)

    @patch("os.remove", side_effect=remove)
    def test_delete_from_cache_last(self, f_remove: MagicMock):
        proxy = Proxy(cache_folder)
        resp = proxy.request("GET", "https://httpbin.org/anything", headers={'Accept': 'text/json'})
        self.assertIsNotNone(resp)
        self.assertFalse(f_remove.called)
        proxy.delete_from_cache()
        self.assertTrue(f_remove.called)


class HarProxyTest(unittest.TestCase):
    def test_load_har(self):
        proxy = HarProxy(os.path.join(*Har.WW_WMW_COVER_C1))
        self.assertIsNotNone(proxy)
        self.assertIsNotNone(proxy.har)

    def test_request(self):
        proxy = HarProxy(os.path.join(*Har.WW_WMW_COVER_C1))
        self.assertIsNotNone(proxy.request("GET", "https://www.wuxiaworld.com/novel/warlock-of-the-magus-world"))

    def test_request_fail(self):
        proxy = HarProxy(os.path.join(*Har.WW_WMW_COVER_C1))
        with self.assertRaises(LookupError):
            proxy.request("GET", "https://www.wuxiaworld.com/novel/warlock-of-the-magus-world/")
        with self.assertRaises(LookupError):
            proxy.request("GET", "http://www.wuxiaworld.com/novel/warlock-of-the-magus-world")
        with self.assertRaises(LookupError):
            proxy.request("GET", "www.wuxiaworld.com/novel/warlock-of-the-magus-world")

    def test_image_request(self):
        proxy = HarProxy(os.path.join(*Har.WW_WMW_COVER_C1))
        self.assertIsNotNone(proxy.request("GET", "https://cdn.wuxiaworld.com/images/covers/wmw.jpg?ver"
                                                  "=2839cf223fce0da2ff6da6ae32ab0c4e705eee1a"))
