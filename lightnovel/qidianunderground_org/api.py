from typing import List, Dict, Generator, Tuple

from bs4 import BeautifulSoup
from bs4.element import Tag
from requests.cookies import create_cookie
from spoofbot.adapter import FileCacheAdapter
from urllib3.util.url import parse_url, Url

from api import UNKNOWN
from lightnovel import ChapterEntry, Book, Novel, Chapter, LightNovelApi, NovelEntry
from util.privatebin import decrypt


class QidianUndergroundOrg:
    _hoster_homepage: Url = parse_url('https://toc.qidianunderground.org')
    _hoster: str = 'QidianUnderground'
    _hoster_abbreviation: str = 'QU'


class QidianUndergroundOrgChapterEntry(QidianUndergroundOrg, ChapterEntry):
    _from_index: int
    _to_index: int

    def __init__(self, url: Url, from_index: int, to_index: int):
        super().__init__(url, f"{from_index} - {to_index}")
        self._from_index = from_index
        self._to_index = to_index

    @property
    def from_index(self) -> int:
        return self._from_index

    @property
    def to_index(self) -> int:
        return self._to_index

    @property
    def spoof_url(self) -> Url:
        return parse_url(f"https://{self.url.hostname}/{self.url.query}.html")


class QidianUndergroundOrgNovel(QidianUndergroundOrg, Novel):
    _index_to_chapter_entry: Dict[int, QidianUndergroundOrgChapterEntry]
    _link_to_document: Dict[Url, BeautifulSoup]

    def __init__(self, title: str, document: BeautifulSoup):
        super().__init__(Url(self._hoster_homepage.scheme, host=self._hoster_homepage.hostname), document)
        self._title = title
        self._index_to_chapter_entry = {}
        self._link_to_document = {}

    @property
    def index_to_chapter_entry(self) -> Dict[int, QidianUndergroundOrgChapterEntry]:
        return self._index_to_chapter_entry

    @property
    def link_to_document(self) -> Dict[Url, BeautifulSoup]:
        return self._link_to_document

    def parse(self) -> bool:
        """Parses this novel's document

        :returns: True if the parsing was successful. False otherwise.
        """
        self._success = self._parse()
        self._ensure_vars_changed({
            '_document': None,
            '_title': UNKNOWN,
            '_author': UNKNOWN,
            '_language': UNKNOWN,
            '_rights': None,
            '_books': [],
            '_first_chapter_path': None,
        })
        return self._success

    def _parse(self) -> bool:
        # html body section.section div.container div.content p
        # noinspection PyTypeChecker
        self._description = None
        self._rights = ''
        self._language = 'en'
        self._author = ''
        self._translator = ''
        book = QidianUndergroundOrgBook(self._title)
        for anchor in self._get_chapter_links():
            indices = anchor.next.string
            if ' - ' in indices:
                from_idx, to_idx = tuple(map(int, indices.split(' - ')))
            else:
                from_idx = int(indices)
                to_idx = from_idx
            entry = QidianUndergroundOrgChapterEntry(parse_url(anchor.get('href')), from_idx, to_idx)
            for idx in range(from_idx, to_idx + 1):
                self._index_to_chapter_entry[idx] = entry
            book.chapter_entries.append(entry)
        self._books = [book]
        url = book.chapter_entries[0].url
        self._first_chapter_path = f"{url.path}?{url.query}"
        return True

    def _get_chapter_links(self) -> List[Tag]:
        tag: Tag
        next_is_chapter_list = False
        content_div = self._document.select_one('div.content')
        if not isinstance(content_div, Tag):
            raise Exception("Unexpected type of tag selection")
        for tag in content_div.contents:
            if next_is_chapter_list and isinstance(tag, Tag) and tag.name == 'ul':
                return tag.select('a')
            next_is_chapter_list |= (tag.name == 'p' and tag.next.strip() == self._title)
        raise LookupError(f"{self.quoted_title} not found in HTML content")

    def generate_chapter_entries(self) -> Generator[Tuple['Book', 'ChapterEntry'], None, None]:
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


class QidianUndergroundOrgBook(QidianUndergroundOrg, Book):
    _chapter_entries: List[QidianUndergroundOrgChapterEntry] = []
    _chapters: List['QidianUndergroundOrgChapter'] = []


class QidianUndergroundOrgNovelEntry(QidianUndergroundOrg, NovelEntry):
    complete: bool

    def __init__(self, title: str, complete: bool):
        super().__init__(Url(self._hoster_homepage.scheme, host=self._hoster_homepage.hostname, path='/'), title)
        self.complete = complete

    def __str__(self):
        if self.complete:
            return f"{self.title} (Complete)"
        return self.title


class QidianUndergroundOrgChapter(QidianUndergroundOrg, Chapter):
    def __init__(self, url: Url, document: BeautifulSoup, index: int):
        super().__init__(url, document)
        self._index = index

    def _parse(self) -> bool:
        self._content = self._select_html()
        if self._content is None:
            return False
        self._title = str(self._content.select_one('h2').next)
        self._language = 'en'
        return True

    def _select_html(self) -> Tag:
        for div in self._document.select('body div.input-group.text-justify.center-block.col-md-8.col-md-offset-2'):
            if div.get('id').endswith(f"chapter-{self._index}"):
                return div
        self.log.error(f"Could not find chapter {self._index}")

    def is_complete(self) -> bool:
        return True

    def clean_content(self):
        pass


class QidianUndergroundOrgApi(QidianUndergroundOrg, LightNovelApi):
    _document: BeautifulSoup = None
    _novel: QidianUndergroundOrgNovel = None

    @property
    def active_novel(self) -> QidianUndergroundOrgNovel:
        return self._novel

    @active_novel.setter
    def active_novel(self, value: QidianUndergroundOrgNovel):
        self._novel = value

    def get_novel(self, title: str, **kwargs) -> QidianUndergroundOrgNovel:
        self._populate_main_document()
        self._novel = QidianUndergroundOrgNovel(title, self._document)
        self._novel.parse()
        return self._novel

    def _populate_main_document(self):
        if not self._document:
            adapter = self.adapter
            if isinstance(adapter, FileCacheAdapter):
                adapter.use_cache = True
            self._document = self._get_html_document(parse_url('https://toc.qidianunderground.org/'))
            if isinstance(adapter, FileCacheAdapter):
                if not adapter.hit:
                    raise Exception("Cannot get data from raw website. "
                                    "Please copy to cache by hand and name it '.html'")
            # qu_toc_url = parse_url('https://toc.qidianunderground.org/')
            # adapter = self.adapter
            # if isinstance(adapter, FileCacheAdapter):
            #     adapter.use_cache = False
            #
            # # Use cfscrape to climb the cloudflare wall
            # old_session = self._session
            # cfs = cfscrape.create_scraper(old_session)
            # cfs.adapters = old_session.adapters
            # if isinstance(old_session, Browser):
            #     # noinspection PyProtectedMember
            #     cfs.headers = old_session._get_default_headers('GET', qu_toc_url, True)
            # self._session = cfs
            # self._document = self._get_html_document(qu_toc_url)
            #
            # # Restore old session
            # self._session = old_session
            # if isinstance(adapter, FileCacheAdapter):
            #     adapter.use_cache = True
            #     # if not adapter.hit:
            #     #     raise Exception("Cannot get data from raw website. "
            #     #                     "Please copy to cache by hand and name it '.html'")

    def get_chapter(self, index: int, **kwargs) -> QidianUndergroundOrgChapter:
        if not self._novel:
            raise Exception("Active novel not set")
        entry = self._novel.index_to_chapter_entry[index]
        paste_id = entry.url.query
        # key = entry.url.fragment
        if entry.url not in self._novel.link_to_document:
            adapter = self.adapter
            if isinstance(adapter, FileCacheAdapter):
                adapter.next_request_cache_url = entry.spoof_url
            # noinspection SpellCheckingInspection
            if entry.url.hostname == 'priv.atebin.com':
                url = Url('https', host=entry.url.hostname, path=entry.url.path, query=entry.url.query)
                response = self._session.post(url.url, headers={
                    'Accept': 'application/json, text/javascript, */*; q=0.01',
                    'X-Requested-With': 'JSONHttpRequest'
                })
            elif entry.url.hostname == 'paste.tech-port.de':
                # noinspection SpellCheckingInspection
                url = Url('https', host=entry.url.hostname, path=entry.url.path, query=f"pasteid={paste_id}")
                self._session.cookies.set_cookie(
                    create_cookie('lang', 'de', domain=entry.url.hostname, path='/'))
                response = self._session.get(url.url, headers={
                    'Accept': 'application/json, text/javascript, */*; q=0.01',
                    'X-Requested-With': 'JSONHttpRequest'
                })
            else:
                raise Exception(f"Unknown privatebin hoster {entry.url.url}")
            if not response.text.startswith('{'):
                adapter.delete_last()
                raise Exception(f"Private bin seems to be down: {entry.url.url}")
            json_data = response.json()
            assert json_data['id'] == paste_id
            self.log.info("Decrypting privatebin paste.")
            document = decrypt(entry.url, json_data)
            self._novel.link_to_document[entry.url] = BeautifulSoup(document, features="html5lib")
        return QidianUndergroundOrgChapter(entry.url, self._novel.link_to_document[entry.url], index)

    def search(self, title: str = '', complete: bool = None) -> List[QidianUndergroundOrgNovelEntry]:
        self._populate_main_document()
        entries = []
        tag: Tag
        for tag in self._document.select('div.content p'):
            novel_title: str = tag.next.strip()
            next_content = tag.contents[1]
            novel_complete = (
                    isinstance(next_content, Tag) and
                    next_content.name == 'strong' and
                    next_content.next == '(Completed)'
            )
            if title.lower() in novel_title.lower():
                if not complete or complete and complete == novel_complete:
                    entries.append(QidianUndergroundOrgNovelEntry(
                        novel_title,
                        novel_complete
                    ))
        return entries
