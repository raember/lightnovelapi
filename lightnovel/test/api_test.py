import unittest
from lightnovel import LightNovelApi


class ApiFactoryTest(unittest.TestCase):
    def test_no_match(self):
        HOST = 'www.google.com'
        with self.assertRaises(LookupError):
            LightNovelApi.get_api(HOST)

    def test_wuxiaworld(self):
        HOST = 'www.wuxiaworld.com'
        api = LightNovelApi.get_api(HOST)
        self.assertIsNotNone(api)
