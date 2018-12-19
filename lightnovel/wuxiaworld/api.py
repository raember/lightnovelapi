from lightnovel.api import LightNovelApi
from bs4 import BeautifulSoup
from .novel import WuxiaWorldNovel
from .chapter import WuxiaWorldChapter


class WuxiaWorld(LightNovelApi):

    def get_novel(self, novel_path: str) -> WuxiaWorldNovel:
        url = "https://www.wuxiaworld.com{}".format(novel_path)
        response = self._request('GET', url)
        response.raise_for_status()
        bs = BeautifulSoup(response.text, features="html5lib")
        return WuxiaWorldNovel(bs)

    def get_chapter(self, chapter_path: str) -> WuxiaWorldChapter:
        url = "https://www.wuxiaworld.com{}".format(chapter_path)
        response = self._request('GET', url)
        response.raise_for_status()
        bs = BeautifulSoup(response.text, features="html5lib")
        return WuxiaWorldChapter(bs)
