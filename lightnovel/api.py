import logging
import os
import shutil
import time
from typing import List, Tuple
import requests
from bs4 import Tag, BeautifulSoup
from util import slugify


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
    success = False


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

    def get_whole_novel(self, novel_path: str, delay=1.0) -> Tuple[Novel, List[Chapter]]:
        novel = self.get_novel(novel_path)
        chapters = []
        chapter = None
        for book in novel.books:
            for chapter_entry in book.chapters:
                chapter = self.get_chapter(chapter_entry.path)
                if not chapter.success:
                    self.log.warning("Failed verifying chapter.")
                    continue
                time.sleep(delay)
                chapters.append(chapter)
        while chapter.success and chapter.next_chapter_path:
            self.log.debug("Following existing next chapter link({}).".format(chapter.next_chapter_path))
            chapter = self.get_chapter(chapter.next_chapter_path)
            if not chapter.success:
                self.log.warning("Failed verifying chapter.")
                break
            time.sleep(delay)
            chapters.append(chapter)
        return novel, chapters

    def compile_to_latex_pdf(self, novel: Novel, chapters: List[Chapter]):
        from util import LatexHtmlSink
        FOLDER = 'out'
        if os.path.isdir(FOLDER):
            shutil.rmtree(FOLDER)
        novel_title = slugify(novel.title)
        path = os.path.join(FOLDER, novel_title)
        if os.path.isdir(path):
            shutil.rmtree(path)
        os.mkdir(FOLDER)
        os.mkdir(path)
        index = 0
        chapter_titles = []
        converter = LatexHtmlSink()
        for chapter in chapters:
            index += 1
            chapter_title = slugify(chapter.title)
            chapter_path = os.path.join(path, "{}_{}.tex".format(index, chapter_title))
            chapter_titles.append(chapter_title)
            with open(chapter_path, 'w') as f:
                f.write("\\section{{{}}}\n{}".format(chapter_title, converter.parse(chapter.content)))
        with open(os.path.join(FOLDER, novel_title, chapter_title + '.tex'), 'w') as f:
            f.write("""\\documentclass{{article}}
\\begin{{document}}""".format(novel_title))
            for chapter_title in chapter_titles:
                f.write("\\include{{{}}}\n".format(chapter_title))
            f.write("\\end{document}")
