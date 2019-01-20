from urllib3.util import parse_url
import lightnovel.api as lnapi
import lightnovel.wuxiaworld.api as wwapi
from util import request


def get_api(url: str, request_method=request) -> lnapi.LightNovelApi:
    apis = [
        wwapi.WuxiaWorldApi(request_method)
    ]
    parsed = parse_url(url)
    for api in apis:
        label = parse_url(api.host)
        if parsed.host == label.host:
            return api
    raise LookupError("No api found for url {}.".format(url))
