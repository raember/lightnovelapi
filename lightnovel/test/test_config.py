import json
import os
import requests
import logging

DATAFOLDER = 'data'


def load_har(name: str) -> list:
    path = os.path.join(DATAFOLDER, name + ".har")
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
