import unittest

from util import HarProxy, HtmlProxy


class HarProxyTest(unittest.TestCase):
    def test_load_har(self):
        proxy = HarProxy('data/WW_WMW_Cover_C1.har')
        self.assertIsNotNone(proxy)
        self.assertIsNone(proxy.har)
        self.assertTrue(proxy.load())
        self.assertIsNotNone(proxy.har)

    def test_request(self):
        proxy = HarProxy('data/WW_WMW_Cover_C1.har')
        proxy.load()
        self.assertIsNotNone(proxy.request("GET", "https://www.wuxiaworld.com/novel/warlock-of-the-magus-world"))

    def test_request_fail(self):
        proxy = HarProxy('data/WW_WMW_Cover_C1.har')
        proxy.load()
        with self.assertRaises(LookupError):
            proxy.request("GET", "https://www.wuxiaworld.com/novel/warlock-of-the-magus-worl")
        with self.assertRaises(LookupError):
            proxy.request("GETS", "https://www.wuxiaworld.com/novel/warlock-of-the-magus-world")

    def test_image_request(self):
        proxy = HarProxy('data/WW_WMW_Cover_C1.har')
        proxy.load()
        self.assertIsNotNone(proxy.request("GET", "https://cdn.wuxiaworld.com/images/covers/wmw.jpg?ver"
                                                  "=2839cf223fce0da2ff6da6ae32ab0c4e705eee1a"))


class FolderProxyTest(unittest.TestCase):
    def test_load_har(self):
        proxy = HtmlProxy('data/heavenly-jewel-change')
        self.assertIsNotNone(proxy)
        self.assertTrue(proxy.load())

    def test_request(self):
        proxy = HtmlProxy('data/heavenly-jewel-change')
        proxy.load()
        self.assertIsNotNone(proxy.request("GET", "https://www.wuxiaworld.com/novel/heavenly-jewel-change"))

    def test_request_fail(self):
        proxy = HtmlProxy('data/heavenly-jewel-change')
        proxy.load()
        with self.assertRaises(LookupError):
            proxy.request("GET", "https://www.wuxiaworld.com/novel/heavenly-jewel-chang")
        with self.assertRaises(LookupError):
            proxy.request("GET", "https://www.wuxiaworld.com/novel/heavenly-jewel-change/")
        with self.assertRaises(LookupError):
            proxy.request("GETS", "https://www.wuxiaworld.com/novel/heavenly-jewel-change")
