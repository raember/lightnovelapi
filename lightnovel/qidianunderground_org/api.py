from datetime import datetime
from typing import List, Dict

from bs4 import BeautifulSoup
from bs4.element import Tag
from spoofbot.adapter import CacheAdapter
from urllib3.util.url import parse_url, Url

from lightnovel import ChapterEntry, Book, Novel, Chapter, LightNovelApi, SearchEntry
from util.privatebin import decrypt


class QidianUndergroundOrg:
    _hostname = 'toc.qidianunderground.org'


class QidianUndergroundOrgChapterEntry(QidianUndergroundOrg, ChapterEntry):
    _from_index: int
    _to_index: int

    def __init__(self, url: Url, from_index: int, to_index: int):
        super(QidianUndergroundOrgChapterEntry, self).__init__(url, f"{from_index} - {to_index}")
        self._from_index = from_index
        self._to_index = to_index

    @property
    def from_index(self) -> int:
        return self._from_index

    @property
    def to_index(self) -> int:
        return self._to_index


class QidianUndergroundOrgNovel(QidianUndergroundOrg, Novel):
    _index_to_chapter_entry: Dict[int, QidianUndergroundOrgChapterEntry]
    _link_to_document: Dict[Url, BeautifulSoup]

    def __init__(self, title: str, document: BeautifulSoup):
        super(QidianUndergroundOrgNovel, self).__init__(Url('https', host=self._hostname), document)
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
        # html body section.section div.container div.content p
        self._cover_url = ''
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
        self._success = True
        return True

    def _get_chapter_links(self) -> List[Tag]:
        tag: Tag
        next_is_chapter_list = False
        content_div = self._document.select_one('div.content')
        if not isinstance(content_div, Tag):
            raise Exception("Unexpected type of tag selection")
        for tag in content_div.contents:
            if next_is_chapter_list and tag.name == 'ul':
                return tag.select('a')
            next_is_chapter_list |= (tag.name == 'p' and tag.next.strip() == self._title)
        raise LookupError(f"'{self._title}' not found in HTML content")


class QidianUndergroundOrgBook(QidianUndergroundOrg, Book):
    _chapter_entries: List[QidianUndergroundOrgChapterEntry] = []
    _chapters: List['QidianUndergroundOrgChapter'] = []


class QidianUndergroundOrgChapter(QidianUndergroundOrg, Chapter):
    # noinspection SpellCheckingInspection
    _hostname = 'priv.atebin.com'

    def __init__(self, url: Url, document: BeautifulSoup, index: int):
        super(QidianUndergroundOrgChapter, self).__init__(url, document)
        self._index = index

    def parse(self) -> bool:
        self._content = self._select_html()
        self._title = str(self._content.select_one('h2').next)
        self._language = 'en'
        self._previous_chapter_path = ''
        self._next_chapter_path = ''
        self._success = True
        return True

    def _select_html(self) -> Tag:
        for div in self._document.select('body div.input-group.text-justify.center-block.col-md-8.col-md-offset-2'):
            if div.get('id').endswith(f"chapter-{self._index}"):
                return div
        raise LookupError("Could not match chapter by index")

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

    def get_novel(self, title: str) -> QidianUndergroundOrgNovel:
        if not self._document:
            if isinstance(self.adapter, CacheAdapter):
                self.adapter.use_cache = True
            self._document = self._get_document(parse_url('https://toc.qidianunderground.org/index.html'))
            if isinstance(self.adapter, CacheAdapter):
                if not self.adapter.hit:
                    raise Exception("Cannot get data from raw website. "
                                    "Please copy to cache by hand and name it 'index.html'")
        self._novel = QidianUndergroundOrgNovel(title, self._document)
        return self._novel

    def get_chapter(self, index: int) -> QidianUndergroundOrgChapter:
        if not self._novel:
            raise Exception("Active novel not set")
        entry = self._novel.index_to_chapter_entry[index]
        url = Url('https', host=entry.url.hostname, path=entry.url.path, query=entry.url.query)
        if entry.url not in self._novel.link_to_document:
            self.check_wait_condition()
            response = self._browser.post(url.url, headers={
                'X-Requested-With': 'JSONHttpRequest'
            })
            self._last_request_timestamp = datetime.now()
            if not response.text.startswith('{'):
                raise Exception(f"Private bin seems to be down: {entry.url}")
            json_data = response.json()
            self._novel.link_to_document[entry.url] = BeautifulSoup(decrypt(entry.url, json_data), features="html5lib")
        return QidianUndergroundOrgChapter(entry.url, self._novel.link_to_document[entry.url], index)

    def search(self) -> List[SearchEntry]:
        raise NotImplementedError(
            "Qidian Underground does not support any sort of search. Please use get_novel instead.")
