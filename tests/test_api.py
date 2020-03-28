import unittest

from urllib3.util import parse_url

from lightnovel import LightNovelApi


class ApiFactoryTest(unittest.TestCase):
    def test_no_match(self):
        with self.assertRaises(LookupError):
            LightNovelApi.get_api(parse_url('www.google.com'))

    def test_wuxiaworld(self):
        api = LightNovelApi.get_api(parse_url('www.wuxiaworld.com'))
        self.assertIsNotNone(api)
