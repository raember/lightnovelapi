import logging
import os
import re
import shutil
import time
from abc import ABC
from datetime import datetime, timedelta
from io import BytesIO
from typing import List, Any, Tuple, Generator, Optional

from PIL import Image
from bs4 import BeautifulSoup
from bs4.element import Tag
from spoofbot import Browser, Firefox
from spoofbot.adapter import CacheAdapter, HarAdapter
from urllib3.util import parse_url, Url

from util.text import slugify


class LightNovelEntity:
    """An entity that is identified by a url"""
    _url: Url

    def __init__(self, url: Url):
        self.log = logging.getLogger(self.__class__.__name__)
        self._url = url

    @property
    def url(self) -> Url:
        """The url that identifies this object"""
        return self._url

    def alter_url(self, path: str = None) -> Url:
        """Returns a url which uses this object's identifying url as basis and alters it if needed.

        :param path: An alternative path for the url. Defaults to this object's identifying path.
        :rtype: Url
        :returns: A new url with a possibly altered path
        """
        if path is None:
            path = self._url.path
        return Url(self._url.scheme, host=self._url.hostname, port=self._url.port, path=path)

    def __str__(self):
        return str(self._url)


class LightNovelPage(LightNovelEntity):
    """A html document of a light novel page"""
    _document: BeautifulSoup
    _success: bool
    _title: str = ''
    _language: str = ''
    _author: str = ''
    _translator: str = ''

    def __init__(self, url: Url, document: BeautifulSoup):
        super().__init__(url)
        self._document = document
        self._success = False

    @property
    def document(self) -> BeautifulSoup:
        return self._document

    @document.setter
    def document(self, value: BeautifulSoup):
        self._document = value

    @document.deleter
    def document(self):
        del self._document

    @property
    def success(self) -> bool:
        return self._success

    @property
    def title(self) -> Optional[str]:
        return self._title if self._title else None

    @property
    def language(self) -> Optional[str]:
        return self._language if self._language else None

    @property
    def author(self) -> Optional[str]:
        return self._author if self._author else None

    @property
    def translator(self) -> Optional[str]:
        return self._translator if self._translator else None

    def parse(self) -> bool:
        raise NotImplementedError('Must be overwritten')

    def __str__(self):
        return self.title


class Novel(LightNovelPage, ABC):
    _description: Tag = None
    _rights: str = ''
    _tags: List[str] = []
    _books: List['Book'] = []
    _first_chapter_path: str = ''
    _cover_url: str = ''
    _cover: Image.Image = None
    _release_date: datetime = None

    @property
    def description(self) -> Optional[Tag]:
        return self._description if self._description else None

    @property
    def rights(self) -> Optional[str]:
        return self._rights if self._rights else None

    @property
    def tags(self) -> Optional[List[str]]:
        return self._tags if self._tags else None

    @property
    def books(self) -> Optional[List['Book']]:
        return self._books if self._books else None

    @property
    def first_chapter(self) -> Optional[Url]:
        return self.alter_url(self._first_chapter_path) if self._first_chapter_path else None

    @property
    def cover_url(self) -> Optional[Url]:
        return parse_url(self._cover_url) if self._cover_url else None

    @property
    def cover(self) -> Optional[Image.Image]:
        return self._cover if self._cover else None

    @cover.setter
    def cover(self, value: Image.Image):
        self._cover = value

    @property
    def release_date(self) -> Optional[datetime]:
        return self._release_date if self._release_date else None

    def enumerate_chapter_entries(self) -> Generator[Tuple['Book', 'ChapterEntry'], None, None]:
        """Enumerates all the parsed books and their chapter entries and assigns them their index."""
        book_n = 0
        chapter_abs_n = 0
        for book in self.books:
            book_n += 1
            chapter_abs_n += 1
            book.number = book_n
            chapter_n = 0
            for chapter_entry in book.chapter_entries:
                chapter_n += 1
                chapter_entry.index = chapter_n
                chapter_entry.abs_index = chapter_abs_n
                self.log.debug(f"Getting chapter entry {book_n}.{chapter_n}({chapter_abs_n}) '{chapter_entry.title}'")
                yield book, chapter_entry

    def __str__(self):
        if self._author:
            return f"'{self._title}' by {self._author} ({len(self._books)} books)"
        return f"'{self._title}' ({len(self._books)} books)"


class Book:
    _title: str = ''
    _chapter_entries: List['ChapterEntry'] = []
    _chapters: List['Chapter'] = []
    _novel: 'Novel' = None
    _index: int = 0

    def __init__(self, title: str):
        self._title = title
        self._chapter_entries = []
        self._chapters = []

    @property
    def title(self) -> str:
        return self._title

    @property
    def chapter_entries(self) -> List['ChapterEntry']:
        return self._chapter_entries

    @property
    def chapters(self) -> List['Chapter']:
        return self._chapters

    @property
    def novel(self) -> 'Novel':
        return self._novel

    @novel.setter
    def novel(self, value: 'Novel'):
        self._novel = value

    @property
    def index(self) -> int:
        return self._index

    @index.setter
    def index(self, value: int):
        self._index = value

    def __copy__(self) -> 'Book':
        book = type(self)(self._title)
        book._chapter_entries = self._chapter_entries.copy()
        book._chapters = self._chapters.copy()
        book._novel = self._novel
        book._index = self._index
        return book

    def __str__(self):
        return f"{self._index} {self._title} ({len(self.chapter_entries)} entries, {len(self.chapters)} chapters)"


class ChapterEntry(LightNovelEntity):
    _title: str = ''
    _index: int = 0
    _abs_index: int = 0

    def __init__(self, url: Url, title: str):
        super(ChapterEntry, self).__init__(url)
        self._title = title

    @property
    def title(self) -> str:
        return self._title

    @property
    def index(self) -> int:
        return self._index

    @index.setter
    def index(self, value: int):
        self._index = value

    @property
    def abs_index(self) -> int:
        return self._abs_index

    @abs_index.setter
    def abs_index(self, value: int):
        self._abs_index = value

    def __str__(self):
        return self._title


class Chapter(LightNovelPage, ABC):
    _previous_chapter_path: str
    _next_chapter_path: str
    _content: Tag = None
    _book: Book = None
    _index: int = 0

    @property
    def content(self) -> Optional[Tag]:
        if not self._content:
            self.log.warning("Content not parsed yet.")
            return None
        return self._content

    @property
    def index(self) -> int:
        return self._index

    @index.setter
    def index(self, value: int):
        self._index = value

    @property
    def previous_chapter(self) -> Optional[Url]:
        return self.alter_url(self._previous_chapter_path) if self._previous_chapter_path else None

    @property
    def next_chapter(self) -> Optional[Url]:
        return self.alter_url(self._next_chapter_path) if self._next_chapter_path else None

    @property
    def book(self) -> Optional[Book]:
        return self._book if self._book else None

    def extract_clean_title(self) -> str:
        """Try to get the title as clean as possible"""
        title = self._title.strip()
        match = re.compile(r'^chapter\s+[(\[]?\s*(\d+)\s*[)\]\-:]*\s*', re.IGNORECASE).search(title)
        if match is not None:
            title = self._cut_match(match, title)
        match = re.compile(r'[(\[]?(\d+[A-Z]?)[)\]]?$').search(title)
        if match is not None:
            title = self._cut_match(match, title)
        title = title.strip('–- ')
        return title if len(title) > 3 else self._title.strip()

    @staticmethod
    def _cut_match(match, string: str) -> str:
        return string[:match.span(0)[0]] + string[match.span(0)[1]:]

    def is_complete(self) -> bool:
        """Whether the chapter has been completely published or not (partial/restricted access)"""
        raise NotImplementedError

    def clean_content(self):
        """Clean the content of the chapter"""
        raise NotImplementedError

    def __del__(self):
        if self._book is not None:
            del self._book
        if self._content is not None:
            del self._content

    def __str__(self):
        if self._book is None:
            if self._title == '':
                return f"?.{self._index}"
            return f"?.{self._index} {self.extract_clean_title()}"
        return f"{self._book.index}.{self._index} {self.extract_clean_title()}"


class SearchEntry(LightNovelEntity):
    title: str


class LightNovelApi(ABC):
    _hostname: str
    _browser: Browser
    _last_request_timestamp: datetime
    _request_delay: timedelta

    def __init__(self, browser: Browser = Firefox(), delay: timedelta = timedelta(seconds=1.0)):
        """
        Creates a new API for a specific service.
        :param browser: The browser to use when executing http requests.
        """
        self.log = logging.getLogger(self.__class__.__name__)
        self._browser = browser
        self._last_request_timestamp = datetime(1, 1, 1)
        self._request_delay = delay
        if type(browser.session.get_adapter('https://')) not in [CacheAdapter, HarAdapter]:
            self.log.warning("Not using a CacheAdapter will take a long time for every run.")

    @property
    def hostname(self) -> str:
        return self._hostname

    @property
    def browser(self) -> Browser:
        return self._browser

    @browser.setter
    def browser(self, value: Browser):
        self._browser = value

    @property
    def adapter(self):
        return self._browser.session.get_adapter('https://')

    @property
    def last_request_timestamp(self) -> datetime:
        return self._last_request_timestamp

    @last_request_timestamp.setter
    def last_request_timestamp(self, value: datetime):
        self._last_request_timestamp = value

    @property
    def request_delay(self) -> timedelta:
        return self._request_delay

    @request_delay.setter
    def request_delay(self, value: timedelta):
        self._request_delay = value

    def _get_document(self, url: Url, **kwargs: Any) -> BeautifulSoup:
        """
        Downloads an html document from a given url.
        :param url: The url where the document is located at.
        :param kwargs: Additional args to convey to the requests library.
        :return: An instance of BeautifulSoup which represents the html document.
        """
        self.check_wait_condition()
        kwargs.setdefault('headers', {}).setdefault('Accept', 'text/html')
        response = self._browser.navigate(str(url), **kwargs)
        self._last_request_timestamp = datetime.now()
        return BeautifulSoup(response.text, features="html5lib")

    def get_novel(self, url: Url) -> Novel:
        """
        Downloads the main page of the novel from the given url.
        :param url: The url where the page is located at.
        :return: An instance of a Novel.
        """
        return Novel(url, self._get_document(url))

    def get_image(self, url: Url) -> Image.Image:
        """
        Downloads an image from a url.
        :param url: The url of the image.
        :return: An image object representation.
        """
        response = self._browser.get(url.url)
        self._last_request_timestamp = datetime.now()
        return Image.open(BytesIO(response.content))

    def get_chapter(self, url: Url) -> Chapter:
        """
        Downloads a chapter from the given url.
        :param url: The url where the chapter is located at.
        :return: An instance of a Chapter.
        """
        return Chapter(url, self._get_document(url))

    def get_entire_novel(self, url: Url) -> Tuple[Novel, Generator[Tuple[Book, Chapter], None, None]]:
        """
        Downloads the main page of a novel (including its image) and then all its chapters.
        It also links the chapters to the corresponding books and the image with the novel.
        This method does not only try to get the chapters from the chapter list
        on the main page, but also follows the links to the next chapter if they
        are available on the current chapter.

        If the main page did not get parsed properly, the function returns the parsed novel
        and an empty list.
        :param url: The url where the main page of the novel is located at.
        :return: A tuple with an instance of the Novel, an image and a list of the downloaded chapters.
        """
        novel = self.get_novel(url)
        if not novel.parse():
            self.log.warning("Couldn't parse novel page. No chapters will be extracted.")

            def empty_gen():
                yield from ()

            return novel, empty_gen()
        self.log.info(f"Downloading novel {novel.title} ({novel.url}).")
        novel.cover = self.get_image(novel.cover_url)
        return novel, self.get_all_chapters(novel)

    def get_all_chapters(self, novel: Novel) -> Generator[Tuple[Book, Chapter], None, None]:
        """
        Creates a generator that downloads all the available chapters of a novel, including
        those that aren't listed on the front page of the novel.

        The generator can be fed into various pipelines.
        :param novel: The novel from which the chapters should be downloaded. Has to be parsed already.
        :return: A generator that downloads each chapter.
        """
        chapter_index = 0
        book = None
        chapter = None
        for book, chapter_entry in novel.enumerate_chapter_entries():
            chapter_index = chapter_entry.index
            chapter = self.get_chapter(chapter_entry.url)
            chapter.index = chapter_entry.index
            yield book, chapter
        while chapter.success and chapter.next_chapter:
            chapter_index += 1
            self.log.debug(f"Following existing next chapter link({chapter.next_chapter}).")
            chapter = self.get_chapter(chapter.next_chapter)
            chapter.index = chapter_index
            yield book, chapter

    def check_wait_condition(self):
        """
        Waits until the proxy request delay expires.
        The delay will be omitted if the last request was a hit in the cache.
        """
        adapter = self._browser.session.get_adapter('https://')
        if isinstance(adapter, CacheAdapter):
            if adapter.hit:
                self.log.debug("Hit in cache. No need to wait")
                return
        self.await_timeout()

    def await_timeout(self):
        now = datetime.now()
        wait_until = self._last_request_timestamp + self._request_delay
        if now < wait_until:
            wait_remainder = wait_until - now
            self.log.debug(f"Waiting for {wait_remainder.total_seconds()} seconds")
            time.sleep(wait_remainder.total_seconds())
        else:
            self.log.debug("Delay already expired. No need to wait")

    def search(self, **kwargs) -> List[SearchEntry]:
        """
        Searches for a novel by title.
        :param kwargs: The search parameters to use.
        :return: A list of SearchEntry.
        """
        raise NotImplementedError

    # TODO: Get rid of this atrocity and use a proper architecture to deal with this instead.
    @staticmethod
    def compile_to_latex_pdf(novel: Novel, chapters: List[Chapter], folder: str):
        from util import LatexHtmlSink
        if os.path.isdir(folder):
            shutil.rmtree(folder)
        novel_title = slugify(novel.title)
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
            chapter_title = slugify(chapter.title)
            chapter_filename_no_ext = f"{index}_{chapter_title}"
            chapter_path = os.path.join(path, chapter_filename_no_ext + '.tex')
            chapter_filenames_no_ext.append(chapter_filename_no_ext)
            with open(chapter_path, 'w') as f:
                f.write(f"\\chapter{{{chapter.title}}}\n{converter.parse(chapter.content)}")
        with open(os.path.join(folder, novel_title, novel_title + '.tex'), 'w') as f:
            # noinspection SpellCheckingInspection
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
    def get_api(url: str, browser: Browser) -> 'LightNovelApi':
        """
        Probes all available api wrappers and returns the first one that matches with the url.
        :param url: The url to be checked for.
        :param browser: The browser to use for the LightNovelApi.
        :return: An instance of a LightNovelApi.
        """
        from wuxiaworld_com import WuxiaWorldComApi
        apis = [
            WuxiaWorldComApi(browser)
        ]
        parsed = parse_url(url)
        for api in apis:
            if parsed.host == api.hostname:
                return api
        raise LookupError(f"No api found for url {url}.")
