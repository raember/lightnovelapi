import unittest
import json
import os
import requests
import logging
import os.path
from typing import List
from enum import Enum


def load_har(name: str) -> list:
    path = name + ".har"
    with open(path, 'r') as fp:
        return json.load(fp)


def mock_request(method: str, url: str, har) -> requests.Response:
    log = logging.getLogger('RequestMock')
    log.info("Received {} request to {}".format(method, url))
    for entry in har:
        if entry['request']['method'] == method and entry['request']['url'] == url:
            class ResponseMock:
                pass

            response = ResponseMock()
            response.url = url
            response.text = entry['response']['content']['text']
            response.content = response.text.encode('utf-8')

            def mock_raise_for_status():
                pass

            def mock_json():
                return json.loads(response.content)

            response.raise_for_status = mock_raise_for_status
            response.json = mock_json
            response.cookies = entry['response']['cookies']
            response.status_code = entry['response']['status']
            return response
    log.info("No entry found...")
    raise LookupError("Couldn't find a response to {} request to {}".format(method, url))


class HarTestCase(unittest.TestCase):
    HAR = []

    @classmethod
    def setUpClass(cls):
        cls.HAR = load_har(os.path.join(*cls.get_har_filename()))

    @classmethod
    def get_har_filename(cls) -> List[str]:
        raise NotImplementedError('Must be overwritten.')

    def _request(self, method: str, url: str, **kwargs):
        return mock_request(method, url, self.HAR)


DATAFOLDER = 'data'


class Hars(Enum):
    WW_HJC_COVER_C1_2 = [DATAFOLDER, 'WW_HJC_Cover_C1-2']
    WW_WMW_COVER_C1 = [DATAFOLDER, 'WW_WMW_Cover_C1']
