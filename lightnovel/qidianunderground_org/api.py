from datetime import datetime
from typing import List, Dict, Generator, Tuple

from bs4 import BeautifulSoup
from bs4.element import Tag
from requests import HTTPError
from requests.cookies import create_cookie
from spoofbot.adapter import FileCacheAdapter
from urllib3.util.url import parse_url, Url

from lightnovel import ChapterEntry, Book, Novel, Chapter, LightNovelApi, NovelEntry
from lightnovel.api import UNKNOWN
from lightnovel.util.privatebin import decrypt
from lightnovel.util.text import unescape_string


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
    _chapters: List[dict]

    def __init__(self, title: str, chapters: list):
        # noinspection PyTypeChecker
        super().__init__(Url(self._hoster_homepage.scheme, host=self._hoster_homepage.hostname), None)
        self._title = title
        self._index_to_chapter_entry = {}
        self._link_to_document = {}
        self._chapters = chapters

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
            # '_document': None,
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
        for segment in self._chapters:
            indices = segment['Text']
            if ' - ' in indices:
                from_idx, to_idx = tuple(map(int, indices.split(' - ')))
            else:
                from_idx = int(indices)
                to_idx = from_idx
            entry = QidianUndergroundOrgChapterEntry(parse_url(segment['Href']), from_idx, to_idx)
            for idx in range(from_idx, to_idx + 1):
                self._index_to_chapter_entry[idx] = entry
            book.chapter_entries.append(entry)
        self._books = [book]
        url = book.chapter_entries[0].url
        self._first_chapter_path = f"{url.path}?{url.query}"
        return True

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
    novel_id: str
    last_update: datetime

    def __init__(self, title: str, novel_id: str, last_update: datetime, complete: bool):
        super().__init__(Url(self._hoster_homepage.scheme, host=self._hoster_homepage.hostname, path='/'), title)
        self.novel_id = novel_id
        self.last_update = last_update
        self.complete = complete

    def __str__(self):
        if self.complete:
            return f"{super().__str__()} (Complete)"
        return super().__str__()


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
    _novels: List[QidianUndergroundOrgNovelEntry] = []
    _novel: QidianUndergroundOrgNovel = None

    @property
    def novel_url(self) -> str:
        return self._novel.url if self._novel is not None else ''

    @property
    def active_novel(self) -> QidianUndergroundOrgNovel:
        return self._novel

    @active_novel.setter
    def active_novel(self, value: QidianUndergroundOrgNovel):
        self._novel = value

    def get_novel(self, novel_entry: QidianUndergroundOrgNovelEntry, **kwargs) -> QidianUndergroundOrgNovel:
        # https://toc.qidianunderground.org/api/v1/pages/public -> title to Id
        # https://toc.qidianunderground.org/api/v1/pages/public/chapters   ???
        # https://toc.qidianunderground.org/api/v1/pages/public/b984e3b6625ce22f/chapters -> chapters of title
        self._populate_novel_list()
        chapters = list(self._get_json_document(
            parse_url(f"https://toc.qidianunderground.org/api/v1/pages/public/{novel_entry.novel_id}/chapters")
        ))
        self._novel = QidianUndergroundOrgNovel(novel_entry.title, chapters)
        self._novel.parse()
        return self._novel

    def _populate_novel_list(self):
        if not self._novels:
            adapter = self.adapter
            if isinstance(adapter, FileCacheAdapter):
                adapter.use_cache = True
            novels = self._get_json_document(parse_url('https://toc.qidianunderground.org/api/v1/pages/public'))
            for novel in novels:
                self._novels.append(QidianUndergroundOrgNovelEntry(
                    title=novel['Name'].replace(u'\xa0', ' '),
                    novel_id=novel['ID'],
                    last_update=datetime.utcfromtimestamp(int(novel['LastUpdated'])),
                    complete=(novel.get('Status', '(Airing)') == '(Completed)')  # (Completed), (Trial) or non existent
                ))

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
            elif entry.url.hostname == 'vim.cx':
                url = Url('https', host=entry.url.hostname, path=entry.url.path, query=f"pasteid={paste_id}")
                response = self._session.get(url.url, headers={
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
            try:
                response.raise_for_status()
            except HTTPError as ex:
                adapter.delete_last()
                raise Exception(f"Failed to fetch privatebin paste: {ex}")
            json_data = response.json()
            assert json_data['id'] == paste_id
            self.log.info("Decrypting privatebin paste.")
            document = decrypt(entry.url, json_data)
            self._novel.link_to_document[entry.url] = BeautifulSoup(document, features="html5lib")
        return QidianUndergroundOrgChapter(entry.url, self._novel.link_to_document[entry.url], index)

    def search(self, title: str = '', complete: bool = None) -> List[QidianUndergroundOrgNovelEntry]:
        self._populate_novel_list()
        entries = []
        for novel in self._novels:
            if title.lower().strip() in novel.title.lower().strip():
                if not complete or complete and complete == novel.complete:
                    entries.append(novel)
        return entries
