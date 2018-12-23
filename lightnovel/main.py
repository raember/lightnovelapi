from lightnovel import WuxiaWorldApi
from lightnovel.test.test_config import Hars, load_har, mock_request, DATAFOLDER
import os

har = load_har(os.path.join('test', *Hars.WW_SFF_Cover_C1_78F.value))


def request(method: str, url: str, **kwargs):
    return mock_request(method, url, har)


api = WuxiaWorldApi(request)
# chapter = api.get_chapter('/novel/stop-friendly-fire/sff-chapter-75')
# novel = {}
# chapters = {}
novel, chapters = api.get_whole_novel('/novel/stop-friendly-fire', 0.0)
api.compile_to_latex_pdf(novel, chapters)
