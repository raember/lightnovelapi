import logging
import os
import time
from typing import List

import requests
from bs4 import Tag, BeautifulSoup


def request(method: str, url: str, **kwargs) -> requests.Response:
    return requests.request(method, url, **kwargs)


def ipinfo():
    return request('GET', 'https://ipinfo.io/json').json()


class LogBase:
    def __init__(self):
        self.log = logging.getLogger(self.__class__.__name__)


class LightNovelEntity(LogBase):
    host = ''

    def get_url(self, path=''):
        return self.host + path


class LightNovelPage(LightNovelEntity):
    path = ''

    def __init__(self, document: BeautifulSoup):
        super().__init__()
        self.log.debug('Extracting data from html.')
        self._parse(document)

    def _parse(self, document: BeautifulSoup):
        raise NotImplementedError('Must be overwritten')

    def get_url(self, path: str = None):
        if path is not None:
            return self.host + path
        else:
            return self.host + self.path


class Chapter(LightNovelPage):
    title = ''
    translator = ''
    previous_chapter_path = ''
    next_chapter_path = ''
    content: Tag = None


class ChapterEntry:
    title = ''
    path = ''


class Book:
    title = ''
    chapters: List[ChapterEntry] = []


class Novel(LightNovelPage):
    title = ''
    translator = ''
    description: Tag = None
    books: List[Book] = []
    first_chapter_path = ''
    img_url = ''


class LightNovelApi(LightNovelEntity):
    def __init__(self, request_method=request):
        super().__init__()
        self._request = request_method

    def _get_document(self, path: str) -> BeautifulSoup:
        response = self._request('GET', self.get_url(path))
        response.raise_for_status()
        return BeautifulSoup(response.text, features="html5lib")

    def get_novel(self, novel_path: str) -> Novel:
        return Novel(self._get_document(novel_path))

    def get_chapter(self, chapter_path: str) -> Chapter:
        return Chapter(self._get_document(chapter_path))

    def get_whole_novel(self, novel_path: str, delay=1.0):
        novel = self.get_novel(self.get_url(novel_path))
        chapters = []
        chapter = None
        for book in novel.books:
            for chapter_entry in book.chapters:
                chapter = self.get_chapter(self.get_url(chapter_entry.path))
                time.sleep(delay)
                chapters.append(chapter)
        while chapter.next_chapter_path:
            chapter = self.get_chapter(self.get_url(chapter.next_chapter_path))
            time.sleep(delay)
            chapters.append(chapter)
        return novel, chapters

    def compile_to_latex_pdf(self, novel: Novel, chapters: List[Chapter]):
        from util import LatexHtmlSink
        FOLDER = 'out'
        path = os.path.join(FOLDER, novel.title)
        if os.path.isdir(path):
            os.rmdir(path)
        os.mkdir(path)
        index = 0
        chapter_names = []
        converter = LatexHtmlSink()
        for chapter in chapters:
            index += 1
            chapter_name = os.path.join(path, "{} - {}.tex".format(index, chapter.title))
            chapter_names.append(chapter_name)
            with open(chapter_name, 'w') as f:
                f.write("\\section{{{}}}\n{}".format(chapter_name, converter.parse(chapter.content)))
