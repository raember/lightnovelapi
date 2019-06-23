import unittest

from lightnovel import LightNovelApi


class ApiFactoryTest(unittest.TestCase):
    def test_no_match(self):
        with self.assertRaises(LookupError):
            LightNovelApi.get_api('www.google.com')

    def test_wuxiaworld(self):
        api = LightNovelApi.get_api('www.wuxiaworld.com')
        self.assertIsNotNone(api)
