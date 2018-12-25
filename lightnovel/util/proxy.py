import json
import logging
from typing import List, Dict

import requests


class Proxy:
    path = ''
    har: List[Dict] = None

    def __init__(self, har_filepath):
        self.log = logging.getLogger(self.__class__.__name__)
        self.path = har_filepath

    def load(self) -> bool:
        try:
            with open(self.path, 'r') as fp:
                self.har = json.load(fp)
        except:
            return False
        return True

    def request(self, method: str, url: str) -> requests.Response:
        self.log.info("Received {} request to {}".format(method, url))
        for entry in self.har:
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
        raise LookupError("No entry found")
