import unittest
import lightnovel.util.factory


class ApiFactoryTest(unittest.TestCase):
    def test_no_match(self):
        HOST = 'www.google.com'
        with self.assertRaises(LookupError):
            lightnovel.util.get_api(HOST)

    def test_wuxiaworld(self):
        HOST = 'www.wuxiaworld.com'
        api = lightnovel.util.get_api(HOST)
        self.assertIsNotNone(api)
