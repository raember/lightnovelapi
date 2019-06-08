import unittest
from unittest.mock import patch
from util import HarProxy, HtmlProxy, DirectProxy
from util.proxy import ResponseMock


def request(method, url, **kwargs):
    return ResponseMock('url', 'str')


class DirectProxyTest(unittest.TestCase):
    @patch("requests.request", side_effect=request)
    def test_request(self, request_mock):
        proxy = DirectProxy()
        resp = proxy.request('GET', 'https://ipinfo.io/json')
        self.assertIsNotNone(resp)
        self.assertEqual('url', resp.url)
        self.assertEqual('str', resp.text)


class HarProxyTest(unittest.TestCase):
    def test_load_har(self):
        proxy = HarProxy('data/WW_WMW_Cover_C1.har')
        self.assertIsNotNone(proxy)
        self.assertIsNotNone(proxy.har)

    def test_request(self):
        proxy = HarProxy('data/WW_WMW_Cover_C1.har')
        self.assertIsNotNone(proxy.request("GET", "https://www.wuxiaworld.com/novel/warlock-of-the-magus-world"))

    def test_request_fail(self):
        proxy = HarProxy('data/WW_WMW_Cover_C1.har')
        with self.assertRaises(LookupError):
            proxy.request("GET", "https://www.wuxiaworld.com/novel/warlock-of-the-magus-world/")
        with self.assertRaises(LookupError):
            proxy.request("GET", "http://www.wuxiaworld.com/novel/warlock-of-the-magus-world")
        with self.assertRaises(LookupError):
            proxy.request("GET", "www.wuxiaworld.com/novel/warlock-of-the-magus-world")

    def test_image_request(self):
        proxy = HarProxy('data/WW_WMW_Cover_C1.har')
        self.assertIsNotNone(proxy.request("GET", "https://cdn.wuxiaworld.com/images/covers/wmw.jpg?ver"
                                                  "=2839cf223fce0da2ff6da6ae32ab0c4e705eee1a"))


class HtmlProxyTest(unittest.TestCase):
    def test_load_har(self):
        proxy = HtmlProxy('../.cache/wuxiaworld/heavenly-jewel-change')
        self.assertIsNotNone(proxy)

    def test_request(self):
        proxy = HtmlProxy('../.cache/wuxiaworld/heavenly-jewel-change')
        self.assertIsNotNone(proxy.request("GET", "https://www.wuxiaworld.com/novel/heavenly-jewel-change"))

    def test_request_fail(self):
        proxy = HtmlProxy('../.cache/wuxiaworld/heavenly-jewel-change')
        with self.assertRaises(LookupError):
            proxy.request("GET", "https://www.wuxiaworld.com/novel/heavenly-jewel-change/")
