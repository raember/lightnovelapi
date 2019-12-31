import unittest

from lightnovel import LightNovelApi
from webot import Firefox


class ApiFactoryTest(unittest.TestCase):
    def test_no_match(self):
        with self.assertRaises(LookupError):
            LightNovelApi.get_api('www.google.com', Firefox())

    def test_wuxiaworld(self):
        api = LightNovelApi.get_api('www.wuxiaworld.com', Firefox())
        self.assertIsNotNone(api)
