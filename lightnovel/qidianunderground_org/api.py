import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Generator, Tuple, Optional

from bs4.element import Tag
from requests import HTTPError
from requests.cookies import create_cookie
from spoofbot.adapter import FileCacheAdapter
from urllib3.util.url import parse_url, Url

from lightnovel import ChapterEntry, Book, Novel, Chapter, LightNovelApi, NovelEntry
from lightnovel.api import HtmlDocument
from lightnovel.util.privatebin import decrypt


class QidianUndergroundOrg:
    _hoster_base_url: Url = parse_url('https://toc.qidianunderground.org')
    _hoster_name: str = 'QidianUnderground'
    _hoster_short_name: str = 'QU'


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
        # For all the cryptbin/privatebin hosters
        return parse_url(f"https://{self.url.hostname}/{self.url.query}")

    def _create_chapter_entry_from_url(self, url: Url) -> 'QidianUndergroundOrgChapterEntry':
        raise NotImplementedError()
        # return QidianUndergroundOrgChapterEntry(url)


class QidianUndergroundOrgNovel(QidianUndergroundOrg, Novel):
    _index_to_chapter_entry: Dict[int, QidianUndergroundOrgChapterEntry]
    _link_to_document: Dict[Url, HtmlDocument]
    _chapters: List[dict]

    def __init__(self, title: str, chapters: list):
        # noinspection PyTypeChecker
        super().__init__(self.change_url(), None)
        self._translators = []
        self._editors = []
        self._tags = []
        self._books = []
        self._title = title
        self._index_to_chapter_entry = {}
        self._link_to_document = {}
        self._chapters = chapters

    @property
    def index_to_chapter_entry(self) -> Dict[int, QidianUndergroundOrgChapterEntry]:
        return self._index_to_chapter_entry

    @property
    def link_to_document(self) -> Dict[Url, HtmlDocument]:
        return self._link_to_document

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

    def __init__(self, url: Url, title: str, novel_id: str, last_update: datetime, complete: bool):
        super().__init__(url, title)
        self.novel_id = novel_id
        self.last_update = last_update
        self.complete = complete

    def __str__(self):
        if self.complete:
            return f"{super().__str__()} (Complete)"
        return super().__str__()


class QidianUndergroundOrgChapter(QidianUndergroundOrg, Chapter):
    # def __init__(self, url: Url, document: HtmlDocument, abs_index: int):
    #     super().__init__(url, document)
    #     self._index = abs_index

    def _parse(self) -> bool:
        self._content = self._select_html()
        if self._content is None:
            return False
        self._title = str(self._content.select_one('h2').next)
        self._language = 'en'
        return True

    def _create_chapter_entry_from_url(self, url: Url) -> 'QidianUndergroundOrgChapterEntry':
        raise NotImplementedError()

    def _select_html(self) -> Tag:
        for div in self.document.content.select(
                'body div.input-group.text-justify.center-block.col-md-8.col-md-offset-2'):
            if div.get('id').endswith(f"chapter-{self._abs_index}"):
                return div
        self.log.error(f"Could not find chapter {self._abs_index}")

    def is_complete(self) -> bool:
        return True

    def clean_content(self):
        pass


class QidianUndergroundOrgApi(QidianUndergroundOrg, LightNovelApi):
    _novels: List[QidianUndergroundOrgNovelEntry] = []
    _novel: QidianUndergroundOrgNovel = None
    _keys: dict[str, str] = None

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
        adapter = self.adapter
        if isinstance(adapter, FileCacheAdapter):
            adapter.use_cache = True
        chapters = list(self._get_json_document(
            parse_url(f"https://toc.qidianunderground.org/api/v1/pages/public/{novel_entry.novel_id}/chapters")
        ).content)
        self._novel = QidianUndergroundOrgNovel(novel_entry.title, chapters)
        self._novel.parse()
        return self._novel

    def _populate_novel_list(self):
        if len(self._novels) != 0:
            return
        qu2wn_idx_path = Path('qu2wn.idx.json')
        qu2wn_idx = {}
        if qu2wn_idx_path.exists():
            with open(qu2wn_idx_path, 'r') as fp:
                qu2wn_idx = json.load(fp)
        # adapter = self.adapter
        # if isinstance(adapter, FileCacheAdapter):
        #     adapter.use_cache = True
        novels = self._get_json_document(parse_url('https://toc.qidianunderground.org/api/v1/pages/public'))
        for novel in novels.content:
            title = novel['Name'].replace(u'\xa0', ' ')
            url = self._get_webnovel_url(title, qu2wn_idx)
            if url is None:
                continue
            self._novels.append(QidianUndergroundOrgNovelEntry(
                url=url,
                title=title,
                novel_id=novel['ID'],
                last_update=datetime.utcfromtimestamp(int(novel['LastUpdated'])),
                complete=(novel.get('Status', '(Airing)') == '(Completed)')  # (Completed), (Trial) or non existent
            ))
        with open(qu2wn_idx_path, 'w') as fp:
            json.dump(qu2wn_idx, fp, indent=4)

    def get_chapter(self, abs_index: int, **kwargs) -> QidianUndergroundOrgChapter:
        if not self._novel:
            raise Exception("Active novel not set")
        entry = self._novel.index_to_chapter_entry[abs_index]
        paste_id = entry.url.query
        # key = entry.url.fragment
        if entry.url not in self._novel.link_to_document:
            adapter = self.adapter
            if isinstance(adapter, FileCacheAdapter):
                adapter.next_request_cache_url = entry.spoof_url
            headers = {
                'Accept': 'application/json, text/javascript, */*; q=0.01',
                'X-Requested-With': 'JSONHttpRequest'
            }
            # noinspection SpellCheckingInspection
            if entry.url.hostname == 'priv.atebin.com':
                url = entry.change_url(path=entry.url.path, query=entry.url.query, fragment=None)
            elif entry.url.hostname == 'vim.cx':
                # noinspection SpellCheckingInspection
                url = entry.change_url(path=entry.url.path, query=f"pasteid={paste_id}", fragment=None)
            elif entry.url.hostname == 'paste.tech-port.de':
                # noinspection SpellCheckingInspection
                url = entry.change_url(path=entry.url.path, query=f"pasteid={paste_id}", fragment=None)
                self._session.cookies.set_cookie(
                    create_cookie('lang', 'de', domain=entry.url.hostname, path='/'))
            elif entry.url.hostname == 'pstbn.top':
                # noinspection SpellCheckingInspection
                url = entry.change_url(path=entry.url.path, query=f"pasteid={paste_id}", fragment=None)
            else:
                raise Exception(f"Unknown privatebin hoster {entry.url.url}")

            response = self._session.get(url.url, headers=headers)
            try:
                response.raise_for_status()
            except HTTPError as ex:
                adapter.delete_last()
                raise Exception(f"Failed to fetch privatebin paste: {ex}")
            json_data = response.json()
            status = int(json_data['status'])
            if status != 0:
                self.log.error(json_data.get('message', 'Unknown privatebin error'))
                raise Exception(
                    f"Failed to fetch privatebin paste: {json_data.get('message', 'Unknown privatebin error')}")
            assert json_data['id'] == paste_id
            self.log.debug("Decrypting privatebin paste.")
            document, self._keys = decrypt(entry.url, json_data, keys=self._keys)
            self._novel.link_to_document[entry.url] = HtmlDocument.from_string(document)
        return QidianUndergroundOrgChapter(entry.url, self._novel.link_to_document[entry.url])

    def search(self, title: str = '', complete: bool = None) -> List[QidianUndergroundOrgNovelEntry]:
        self._populate_novel_list()
        entries = []
        for novel in self._novels:
            if title.lower().strip() in novel.title.lower().strip():
                if not complete or complete and complete == novel.complete:
                    entries.append(novel)
        return entries

    def _get_webnovel_url(self, title: str, idx: dict[str, Url]) -> Optional[Url]:
        if title in idx.keys():
            url = idx[title]
            if url is None:
                return None
            return parse_url(url)
        else:
            from webnovel_com import WebNovelComApi
            wn_api = WebNovelComApi(self.session)
            matches = wn_api.search_for_specific_title(title)
            if len(matches) == 0:
                self.log.warning(f"Could not find any matching title on webnovel for '{title}'. Marking as empty.")
                idx[title] = None
                return None
            else:
                match = matches[0]
                if len(matches) > 1:
                    self.log.info(f"Chose {match} out of: {', '.join(map(str, matches))}")
                idx[title] = match.url.url
            return match.url
