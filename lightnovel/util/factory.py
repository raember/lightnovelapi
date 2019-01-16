from urllib3.util import parse_url
from lightnovel import LightNovelApi, WuxiaWorldApi
from util import request


def get_api(url: str, request_method=request) -> LightNovelApi:
    apis = [
        WuxiaWorldApi(request_method)
    ]
    parsed = parse_url(url)
    for api in apis:
        label = parse_url(api.host)
        if parsed.host == label.host:
            return api
    raise LookupError("No api found for url {}.".format(url))
