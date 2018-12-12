from lightnovel.api import LightNovelApi
from bs4 import BeautifulSoup
from .novel import WuxiaWorldNovel


class WuxiaWorld(LightNovelApi):

    def get_novel(self, novel_path: str) -> WuxiaWorldNovel:
        url = "https://www.wuxiaworld.com/novel/{}".format(novel_path.lower())
        response = self._request('GET', url)
        response.raise_for_status()
        bs = BeautifulSoup(response.text, features="html5lib")
        return WuxiaWorldNovel(bs)
