import logging
import os
import shutil
import time
from datetime import datetime
from typing import List, Tuple
import requests
from bs4 import Tag, BeautifulSoup
from util import slugify


def request(method: str, url: str, **kwargs) -> requests.Response:
    return requests.request(method, url, **kwargs)


def ipinfo():
    return request('GET', 'https://ipinfo.io/json').json()


class LightNovelEntity:
    host = ''

    def __init__(self):
        self.log = logging.getLogger(self.__class__.__name__)

    def get_url(self, path=''):
        return self.host + path


class LightNovelPage(LightNovelEntity):
    path = ''
    document = None
    success = False

    def __init__(self, document: BeautifulSoup):
        super().__init__()
        self.log.debug('Extracting data from html.')
        self.document = document
        self.success = self.parse(document)

    def parse(self, document: BeautifulSoup = None) -> bool:
        if not document:
            document = self.document
        try:
            return self._parse(document)
        except Exception as e:
            self.log.error(e)
            return False

    def _parse(self, document: BeautifulSoup) -> bool:
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

    def get_whole_novel(self, novel_path: str, delay=1.0) -> Tuple[Novel, List[Chapter]]:
        # self.log.info('test')
        # self.log.debug('test')
        # self.log.warning('test')
        # self.log.error('test')
        # exit(0)
        novel = self.get_novel(novel_path)
        if not novel.success:
            self.log.warning("Couldn't parse novel page. No chapters will be extracted.")
            return novel, []
        chapters = []
        chapter = None
        for book in novel.books:
            for chapter_entry in book.chapters:
                chapter = self.get_chapter(chapter_entry.path)
                if not chapter.success:
                    self.log.warning("Failed parsing chapter.")
                time.sleep(delay)
                chapters.append(chapter)
            #     break
            # break
        while chapter.success and chapter.next_chapter_path:
            self.log.debug("Following existing next chapter link({}).".format(chapter.next_chapter_path))
            chapter = self.get_chapter(chapter.next_chapter_path)
            if not chapter.success:
                self.log.warning("Failed verifying chapter.")
                break
            time.sleep(delay)
            chapters.append(chapter)
            # break
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
        chapter_filenames_noext = []
        converter = LatexHtmlSink()
        for chapter in chapters:
            index += 1
            chapter_title = slugify(chapter.title)
            chapter_filename_noext = "{}_{}".format(index, chapter_title)
            chapter_path = os.path.join(path, chapter_filename_noext + '.tex')
            chapter_filenames_noext.append(chapter_filename_noext)
            with open(chapter_path, 'w') as f:
                f.write("\\chapter{{{}}}\n{}".format(chapter.title, converter.parse(chapter.content)))
        with open(os.path.join(FOLDER, novel_title, novel_title + '.tex'), 'w') as f:
            f.write("""\\documentclass[oneside,11pt]{{memoir}}
\\input{{structure.tex}}
\\title{{{}}}
\\author{{{}}}
\\newcommand{{\\edition}}{{}}
\\makeatletter\\@addtoreset{{chapter}}{{part}}\makeatother%
\\begin{{document}}
\\thispagestyle{{empty}}
%\\ThisCenterWallPaper{{1.12}}{{cover.jpg}}
\\begin{{tikzpicture}}[remember picture,overlay]
\\node [rectangle, rounded corners, fill=white, opacity=0.75, anchor=south west, minimum width=4cm, minimum height=3cm] (box) at (-0.5,-10) (box){{}};
\\node[anchor=west, color01, xshift=-2cm, yshift=-0.8cm, text width=3.9cm, font=\\sffamily\\bfseries\\scshape\\Large] at (box.north){{\\thetitle}};
\\node[anchor=west, color01, xshift=-2cm, yshift=-1.8cm, text width=3.9cm, font=\\sffamily\\scriptsize] at (box.north){{\\edition}};
\\node[anchor=west, color01, xshift=-2cm, yshift=-2.5cm, text width=3.9cm, font=\\sffamily\\bfseries] at (box.north){{\\theauthor}};
\\end{{tikzpicture}}
\\newpage

\\tableofcontents

\\chapter*{{Synopsis}}
{}
\\newpage
""".format(
                novel.title,
                novel.translator,
                converter.parse(novel.description)
            ))
            for chapter_title in chapter_filenames_noext:
                f.write("\\include{{{}}}\n".format(chapter_title))
            f.write("\\end{document}")
        shutil.copyfile('structure.tex', os.path.join(FOLDER, novel_title, 'structure.tex'))
