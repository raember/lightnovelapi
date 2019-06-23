import logging
import os
import re
import shutil
import time
import urllib.parse
from abc import ABC
from datetime import datetime
from io import BytesIO
from typing import List, Any, Tuple, Generator

import requests
from PIL import Image
from bs4 import Tag, BeautifulSoup
from urllib3.util import parse_url

import lightnovel.util.proxy as proxyutil
import lightnovel.util.text as textutil


class LightNovelEntity:
    host = ''
    path = ''

    def __init__(self):
        self.log = logging.getLogger(self.__class__.__name__)

    def get_url(self, path: str = None):
        if path is not None:
            return urllib.parse.urljoin(self.host, path)
        else:
            return urllib.parse.urljoin(self.host, self.path)


class LightNovelPage(LightNovelEntity):
    title = ''
    path = ''
    document = None
    success = False
    name = 'generic'
    language = 'en'

    def __init__(self, document: BeautifulSoup):
        super().__init__()
        self.document = document

    def parse(self, document: BeautifulSoup = None) -> bool:
        if not document:
            document = self.document
        try:
            self.success = self._parse(document)
        except Exception as e:
            self.log.error(e)
            self.success = False
        finally:
            return self.success

    def _parse(self, document: BeautifulSoup) -> bool:
        raise NotImplementedError('Must be overwritten')

    def __str__(self):
        return self.title


class Chapter(LightNovelPage, ABC):
    translator = ''
    previous_chapter_path = ''
    next_chapter_path = ''
    content: Tag = None
    book: 'Book' = None
    number = 0
    REGEX_CHAPTER_NUMBER = re.compile(r'^chapter\s+[(\[]?\s*(\d+)\s*[)\]\-:]*\s*', re.IGNORECASE)
    REGEX_CHAPTER_SUB_NUMBER = re.compile(r'[(\[]?(\d+)[)\]]?$')

    def get_number(self):
        match = self.REGEX_CHAPTER_NUMBER.search(self.title)
        if match is not None:
            return int(match.group(1))
        return -1

    def get_sub_number(self):
        match = self.REGEX_CHAPTER_SUB_NUMBER.search(self.title)
        if match is not None:
            return int(match.group(1))
        return -1

    def get_title(self):
        title: str = self.title.strip()
        match = self.REGEX_CHAPTER_NUMBER.search(title)
        if match is not None:
            title = self._cut_match(match, title)
        match = self.REGEX_CHAPTER_SUB_NUMBER.search(title)
        if match is not None:
            title = self._cut_match(match, title)
        return title.strip('–- ')

    @staticmethod
    def _cut_match(match, string: str) -> str:
        return string[:match.span(0)[0]] + string[match.span(0)[1]:]

    def is_complete(self) -> bool:
        raise NotImplementedError

    def clean_content(self):
        raise NotImplementedError

    def __del__(self):
        if self.book is not None:
            del self.book
        if self.content is not None:
            del self.content

    def __str__(self):
        if self.book is None:
            if self.title == '':
                return f"?.{self.number}"
            return f"?.{self.number} {self.get_title()}"
        return f"{self.book.number}.{self.number} {self.get_title()}"


class ChapterEntry(LightNovelEntity):
    title = ''
    number = 0

    def __str__(self):
        return self.title


class Book:
    title = ''
    chapter_entries: List[ChapterEntry] = []
    chapters: List[Chapter] = []
    novel: 'Novel'
    number = 0

    def __copy__(self) -> 'Book':
        book = type(self)()
        book.title = self.title
        book.chapter_entries = self.chapter_entries.copy()
        book.chapters = self.chapters.copy()
        book.novel = self.novel
        return book

    def __str__(self):
        return f"{self.number} {self.title} ({len(self.chapters)}/{len(self.chapter_entries)})"


class Novel(LightNovelPage, ABC):
    author = ''
    translator = ''
    rights = ''
    tags: List[str] = []
    description: Tag = None
    books: List[Book] = []
    first_chapter_path = ''
    img_url = ''
    image: Image.Image = None
    date: datetime = datetime.utcfromtimestamp(0)

    def __str__(self):
        return f"'{self.title}' by {self.translator} ({len(self.books)} books)"

    def gen_entries(self) -> Generator[Tuple[int, int, Book, ChapterEntry], None, None]:
        b_n = 0
        for book in self.books:
            b_n += 1
            book.number = b_n
            book.chapters = []
            c_n = 0
            for chapter_entry in book.chapter_entries:
                c_n += 1
                chapter_entry.number = c_n
                self.log.debug(f"Getting chapter entry {b_n}.{c_n} '{chapter_entry.title}'")
                yield book, chapter_entry


class SearchEntry(LightNovelEntity):
    title = ''

    def __str__(self):
        return self.title


class LightNovelApi(LightNovelEntity, ABC):
    proxy: proxyutil.Proxy = None

    def __init__(self, proxy: proxyutil.Proxy = proxyutil.DirectProxy):
        """
        Creates a new API for a specific service.
        :param proxy: The proxy to use when executing http requests.
        """
        super().__init__()
        self.proxy = proxy

    def _get(self, url: str, **kwargs: Any) -> requests.Response:
        """
        Downloads data from a given url.
        :param url: The url where the document is located at.
        :param kwargs: Additional args to convey to the requests library.
        :return: The Response.
        """
        return self.proxy.request('GET', url, **kwargs)

    def _get_document(self, url: str, **kwargs: Any) -> BeautifulSoup:
        """
        Downloads an html document from a given url.
        :param url: The url where the document is located at.
        :param kwargs: Additional args to convey to the requests library.
        :return: An instance of BeautifulSoup which represents the html document.
        """
        if 'headers' not in kwargs:
            kwargs['headers'] = {'Accept': 'text/html'}
        if 'Accept' not in kwargs['headers']:
            kwargs['headers']['Accept'] = 'text/html'
        response = self._get(url, **kwargs)
        return BeautifulSoup(response.text, features="html5lib")

    def get_novel(self, url: str) -> Novel:
        """
        Downloads the main page of the novel from the given url.
        :param url: The url where the page is located at.
        :return: An instance of a Novel.
        """
        return Novel(self._get_document(url))

    def get_image(self, url: str) -> Image.Image:
        return Image.open(BytesIO(self._get(url).content))

    def get_chapter(self, url: str) -> Chapter:
        """
        Downloads a chapter from the given url.
        :param url: The url where the chapter is located at.
        :return: An instance of a Chapter.
        """
        return Chapter(self._get_document(url))

    def get_entire_novel(self, url: str, delay=1.0) -> Tuple[Novel, Generator[Tuple[Book, Chapter], None, None]]:
        """
        Downloads the main page of a novel (including its image) and then all its chapters.
        It also links the chapters to the corresponding books and the image with the novel.
        This method does not only try to get the chapters from the chapter list
        on the main page, but also follows the links to the next chapter if they
        are available on the current chapter.

        If the main page did not get parsed properly, the function returns the parsed novel
        and an empty list.
        :param url: The url where the main page of the novel is located at.
        :param delay: The time duration in seconds for which to wait between downloads.
        :return: A tuple with an instance of the Novel, an image and a list of the downloaded chapters.
        """
        novel = self.get_novel(url)
        if not novel.parse():
            self.log.warning("Couldn't parse novel page. No chapters will be extracted.")

            def empty_gen():
                yield from ()

            return novel, empty_gen()
        novel.image = self.get_image(novel.img_url)

        def get_delay():
            if self.proxy.hit:
                return 0.0
            else:
                return delay

        def get_chapters():
            c_n = 0
            book = None
            for book, chapter_entry in novel.gen_entries():
                c_n = chapter_entry.number
                chapter = self.get_chapter(self.get_url(chapter_entry.path))
                chapter.number = c_n
                yield book, chapter
                time.sleep(get_delay())
            chapter = novel.books[-1].chapters[-1]
            while chapter.success and chapter.next_chapter_path:
                c_n += 1
                self.log.debug(f"Following existing next chapter link({chapter.next_chapter_path}).")
                chapter = self.get_chapter(self.get_url(chapter.next_chapter_path))
                chapter.number = c_n
                yield book, chapter
                time.sleep(get_delay())
        return novel, get_chapters()

    def search(self, title: str) -> List[SearchEntry]:
        """
        Searches for a novel by title.
        :param title: The title to search for.
        :return: A list of SearchEntry.
        """
        raise NotImplementedError

    # TODO: Get rid of this atrocity and use a proper architecture to deal with this instead.
    @staticmethod
    def compile_to_latex_pdf(novel: Novel, chapters: List[Chapter], folder: str):
        from util import LatexHtmlSink
        if os.path.isdir(folder):
            shutil.rmtree(folder)
        novel_title = textutil.slugify(novel.title)
        path = os.path.join(folder, novel_title)
        if os.path.isdir(path):
            shutil.rmtree(path)
        os.makedirs(folder)
        os.makedirs(path)
        index = 0
        chapter_filenames_no_ext = []
        converter = LatexHtmlSink()
        for chapter in chapters:
            index += 1
            chapter_title = textutil.slugify(chapter.title)
            chapter_filename_no_ext = f"{index}_{chapter_title}"
            chapter_path = os.path.join(path, chapter_filename_no_ext + '.tex')
            chapter_filenames_no_ext.append(chapter_filename_no_ext)
            with open(chapter_path, 'w') as f:
                f.write(f"\\chapter{{{chapter.title}}}\n{converter.parse(chapter.content)}")
        with open(os.path.join(folder, novel_title, novel_title + '.tex'), 'w') as f:
            f.write(f"""\\documentclass[oneside,11pt]{{memoir}}
\\usepackage[normalem]{{ulem}}
\\usepackage{{fontspec}}
\\input{{structure.tex}}
\\title{{{novel.title}}}
\\author{{{novel.translator}}}
\\newcommand{{\\edition}}{{}}
\\makeatletter\\@addtoreset{{chapter}}{{part}}\\makeatother%
\\begin{{document}}
\\thispagestyle{{empty}}
%\\ThisCenterWallPaper{{1.12}}{{cover.jpg}}
\\begin{{tikzpicture}}[remember picture,overlay]
\\node[rectangle, rounded corners, fill=white, opacity=0.75, anchor=south west, minimum width=4cm, minimum height=3cm] (box) at (-0.5,-10) (box){{}};
\\node[anchor=west, color01, xshift=-2cm, yshift=-0.8cm, text width=3.9cm, font=\\sffamily\\bfseries\\scshape\\Large] at (box.north){{\\thetitle}};
\\node[anchor=west, color01, xshift=-2cm, yshift=-1.8cm, text width=3.9cm, font=\\sffamily\\scriptsize] at (box.north){{\\edition}};
\\node[anchor=west, color01, xshift=-2cm, yshift=-2.5cm, text width=3.9cm, font=\\sffamily\\bfseries] at (box.north){{\\theauthor}};
\\end{{tikzpicture}}
\\newpage

\\tableofcontents

\\chapter*{{Synopsis}}
{converter.parse(novel.description)}
\\newpage
"""
                    )
            for chapter_title in chapter_filenames_no_ext:
                f.write(f"\\include{{{chapter_title}}}\n")
            f.write("\\end{document}")
        shutil.copyfile('structure.tex', os.path.join(folder, novel_title, 'structure.tex'))

    @staticmethod
    def get_api(url: str, proxy: proxyutil.Proxy = proxyutil.DirectProxy()) -> 'LightNovelApi':
        """
        Probes all available api wrappers and returns the first one that matches with the url.
        :param url: The url to be checked for.
        :param proxy: The proxy to use for the LightNovelApi.
        :return: An instance of a LightNovelApi.
        """
        from wuxiaworld import WuxiaWorldApi
        apis = [
            WuxiaWorldApi(proxy)
        ]
        parsed = parse_url(url)
        for api in apis:
            label = parse_url(api.host)
            if parsed.host == label.host:
                return api
        raise LookupError(f"No api found for url {url}.")
