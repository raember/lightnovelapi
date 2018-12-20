from lightnovel.api import LightNovelApi
from .novel import WuxiaWorldNovel
from .chapter import WuxiaWorldChapter
from . import WuxiaWorld


class WuxiaWorldApi(WuxiaWorld, LightNovelApi):

    def get_novel(self, novel_path: str) -> WuxiaWorldNovel:
        return WuxiaWorldNovel(self._get_document(novel_path))

    def get_chapter(self, chapter_path: str) -> WuxiaWorldChapter:
        return WuxiaWorldChapter(self._get_document(chapter_path))
