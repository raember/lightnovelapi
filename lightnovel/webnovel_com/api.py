import html
import json
import re
from abc import ABC
from datetime import datetime, timedelta
from typing import List, Generator, Tuple, Optional, Any

from bs4 import BeautifulSoup
from bs4.element import Tag, NavigableString
from requests import Session
from requests.cookies import create_cookie
from spoofbot import Browser, MimeTypeTag
from spoofbot.adapter import FileCacheAdapter
from spoofbot.util import encode_form_data
from urllib3.util.url import parse_url, Url

from lightnovel import ChapterEntry, Book, Novel, Chapter, LightNovelApi, NovelEntry, ChapterFetchStrategy, \
    JsonDocument, HtmlDocument
from lightnovel.qidianunderground_org import QidianUndergroundOrgNovel, QidianUndergroundOrgChapter
from lightnovel.util import dict_to_query


class WebNovelCom:
    _hoster_base_url: Url = parse_url('https://www.webnovel.com')
    _hoster_name: str = 'WebNovel'
    _hoster_short_name: str = 'WN'


class WebNovelComChapterEntry(WebNovelCom, ChapterEntry):
    _is_vip: int
    _csrf_token: str
    _book_id: str
    _chapter_id: str
    _timestamp: datetime

    def __init__(self, title: str, is_vip: int, csrf_token: str, book_id: str, chapter_id: str,
                 timestamp: datetime = datetime.now()):
        super().__init__(Url(), title)
        self._is_vip = is_vip
        self._csrf_token = csrf_token
        assert book_id.endswith('05')
        assert book_id.isdigit()
        self._book_id = book_id
        assert chapter_id.isdigit()
        self._chapter_id = chapter_id
        self._timestamp = timestamp
        self._url = parse_url(f"https://www.webnovel.com/go/pcm/chapter/getContent?"
                              f"_csrfToken={csrf_token}&"
                              f"bookId={book_id}&"
                              f"chapterId={chapter_id}&"
                              f"_={int(timestamp.timestamp() * 1000)}")

    @property
    def is_vip(self) -> bool:
        return self._is_vip == 2

    @property
    def csrf_token(self) -> str:
        return self._csrf_token

    @property
    def book_id(self) -> str:
        return self._book_id

    @property
    def chapter_id(self) -> str:
        return self._chapter_id

    @property
    def timestamp(self) -> datetime:
        return self._timestamp

    @property
    def spoof_url(self) -> Url:
        return parse_url(f"https://www.webnovel.com/go/pcm/chapter/{self._book_id}/{self._chapter_id}")

    @property
    def mime_type(self) -> str:
        return 'application/json'

    def _create_chapter_entry_from_url(self, url: Url) -> 'WebNovelComChapterEntry':
        return WebNovelComChapterEntry(url)


class WebNovelComBook(WebNovelCom, Book):
    _chapter_entries: List[WebNovelComChapterEntry] = []
    _chapters: List['WebNovelComChapter'] = []


class WebNovelComNovelEntry(WebNovelCom, NovelEntry):
    id: int

    def __init__(self, json_data: dict):
        self.id = int(json_data['id'])
        super().__init__(
            url=self.change_url(path=f"/book/{self.id}"),
            title=html.unescape(json_data['name']),
        )


class WebNovelComNovel(WebNovelCom, Novel):
    _books: List[WebNovelComBook]
    _session: Session
    _novel_id: str
    _timestamp: datetime

    def __init__(self, url: Url, document: HtmlDocument, session: Session):
        super().__init__(url, document)
        self._session = session
        self._novel_id = ''
        self._timestamp = datetime.now()

    @property
    def novel_id(self) -> str:
        return self._novel_id

    @property
    def timestamp(self) -> datetime:
        return self._timestamp

    @timestamp.setter
    def timestamp(self, value: datetime):
        self._timestamp = value

    def _parse(self) -> bool:
        head = self.document.content.select_one('head')
        if not isinstance(head, Tag):
            raise Exception("Unexpected type of tag selection")
        url = head.select_one('meta[property="og:url"]')
        if not isinstance(url, Tag):
            raise Exception("Unexpected type of tag selection")
        if url.get(
                'content') == 'https://www.webnovel.com/':  # If the novel has been taken down, we will get a redirect to the landing page
            return False
        self._novel_id = parse_url(url.get('content')).path.split('_')[-1]
        description = head.select_one('meta[property="og:description"]')
        if not isinstance(description, Tag):
            raise Exception("Unexpected type of tag selection")
        self._description = self.document.content.new_tag('p')
        self._description.string = html.unescape(description.get('content'))
        rights = self.document.content.select_one('p.g_ft_copy')
        if not isinstance(rights, Tag):
            raise Exception("Unexpected type of tag selection")
        self._rights = html.unescape(rights.text)
        g_data = self.document.content.select_one('body.footer_auto > script')
        if not isinstance(g_data, Tag):
            raise Exception("Unexpected type of tag selection")
        match = re.search(r"g_data\.book ?= (?P<json>{.*});?$", g_data.text, re.MULTILINE)
        if not match:
            raise Exception("Failed to match for json data")
        json_str = match.group('json')
        # https://stackoverflow.com/questions/37689400/dealing-with-mis-escaped-characters-in-json
        json_str2 = re.sub(r'(?<!\\)\\(?!["\\/bfnrt]|u[0-9a-fA-F]{4})', '', json_str)
        json_str3 = re.sub(r'(?<!\\)((\\\\)+)\\(?!\\)', r'\1', json_str2)  # Handle odd numbers of backslashes
        json_data = json.loads(json_str3)['bookInfo']
        self._language = 'en'
        self._author = json_data['authorName']
        self._translators = []
        for translator in json_data.get('translatorItems', []):
            self._translators.append(translator['name'])
        cover_update_time = datetime.fromtimestamp(float(json_data['coverUpdateTime']) / 1000)
        self._cover_url = parse_url(f'https://img.webnovel.com/bookcover/{self._novel_id}/300/300.jpg'
                                    f'?coverUpdateTime={int(cover_update_time.timestamp() * 1000)}')
        self._tags = list(map(lambda i: i['tagName'], json_data.get('tagInfos', [])))
        self._release_date = datetime.fromtimestamp(0)

        adapter = self._session.get_adapter('https://')
        if isinstance(adapter, FileCacheAdapter):
            adapter.next_request_cache_url = parse_url(
                f"https://www.webnovel.com/apiajax/chapter/{self._novel_id}.html"
            )
            adapter.backup_and_miss_next_request = True
        # noinspection SpellCheckingInspection
        chapter_list_url = Url('https', host='www.webnovel.com', path='/go/pcm/chapter/get-chapter-list')
        response = self._session.get(chapter_list_url.url, params={
            '_csrfToken': self._session.cookies.get('_csrfToken'),
            'bookId': self._novel_id,
            'pageIndex': 0,
            '_': int(self._timestamp.timestamp() * 1000),
        })
        json_data = response.json()['data']
        book_info = json_data['bookInfo']
        self._title = book_info['bookName']
        self._books = self.__extract_books(json_data['volumeItems'])
        if len(self._books) == 0:
            self.log.error("No books were found!")
            return False
        first_chapter = self._books[0].chapter_entries[0]
        self._first_chapter_path = f"{first_chapter.url.path}?{first_chapter.url.query}"
        return True

    def __extract_books(self, volume_items: List[dict]) -> List[WebNovelComBook]:
        books = []
        book_index = 0
        for volume in volume_items:
            book_index += 1
            if volume['volumeName'] == '':
                del volume['volumeName']
            book = WebNovelComBook(volume.get('volumeName', f'Volume {book_index}'))
            book.novel = self
            book.index = book_index
            book._chapter_entries = self.__extract_chapters(volume.get('chapterItems', []))
            self.log.debug(f"Book: {book}")
            books.append(book)
        return books

    def __extract_chapters(self, chapter_items: List[dict]) -> List[WebNovelComChapterEntry]:
        chapters = []
        chapter_index = 0
        for chapter_item in chapter_items:
            chapter_index += 1
            chapter = WebNovelComChapterEntry(
                title=chapter_item['chapterName'],  # .encode('latin1').decode('utf8'),  # turns 'â\x80\x99' into '´'
                is_vip=int(chapter_item['isVip']),
                csrf_token=self._session.cookies.get('_csrfToken'),
                book_id=self._novel_id,
                chapter_id=chapter_item['chapterId'],
                timestamp=self._timestamp,
            )
            chapter.index = chapter_index
            chapters.append(chapter)
        self.log.debug(f"Chapters found: {len(chapters)}")
        return chapters


class WebNovelComChapter(WebNovelCom, Chapter):
    _mime_type: MimeTypeTag = MimeTypeTag('application', 'json')
    _document: dict
    _csrf_token: str
    _chapter_id: int
    _is_vip: int
    _timestamp: datetime

    def __init__(self, url: Url, json_data: JsonDocument, csrf_token: str):
        # noinspection PyTypeChecker
        super().__init__(url, json_data)
        self._csrf_token = csrf_token
        self._chapter_id = 0
        self._is_vip = 0
        self._timestamp = datetime.now()
        self._can_handle_wall = True

    @property
    def chapter_id(self) -> int:
        return self._chapter_id

    @property
    def is_vip(self) -> bool:
        return self._is_vip == 2

    @property
    def timestamp(self) -> datetime:
        return self._timestamp

    @timestamp.setter
    def timestamp(self, value: datetime):
        self._timestamp = value

    def _parse(self) -> bool:
        if self.document.content['code'] != 0:
            self.log.error(f"Api returned error {self.document.content['code']}: {self.document.content['msg']}")
            return False
        data = self.document.content['data']
        book_info = data['bookInfo']
        chapter_info = data['chapterInfo']
        self._chapter_id = int(chapter_info['chapterId'])
        self._title = chapter_info['chapterName']
        self._is_vip = int(chapter_info['vipStatus'])
        self._previous_chapter = self.build_url(
            self._csrf_token,
            int(book_info['bookId']),
            chapter_info['preChapterId'],
            self._timestamp,
        )
        self._next_chapter = self.build_url(
            self._csrf_token,
            int(book_info['bookId']),
            chapter_info['nextChapterId'],
            self._timestamp,
        )
        doc = BeautifulSoup('html', features="html5lib")
        self._content = doc.new_tag('div')
        for paragraph in chapter_info['contents']:
            content = re.sub(r"<pirate>.*?</pirate>", '', paragraph['content'])
            for child in BeautifulSoup(content, features="html5lib").body.contents:
                if isinstance(child, NavigableString):
                    text = child.string
                    child = doc.new_tag('p')
                    child.string = text
                self._content.append(child)
        return True

    def _create_chapter_entry_from_url(self, url: Url) -> 'WebNovelComChapterEntry':
        entry = WebNovelComChapterEntry('', 0, '', '05', '0')
        entry._url = url
        return entry

    def is_complete(self) -> bool:
        return not self.is_vip and self._next_chapter is not None

    def clean_content(self):
        pass

    @staticmethod
    def build_url(csrf_token: str, book_id: int, chapter_id: int, timestamp: datetime = datetime.now()
                  ) -> Optional[Url]:
        if chapter_id == -1:
            return None
        # noinspection SpellCheckingInspection
        return Url('https', host='www.webnovel.com', path='/go/pcm/chapter/getContent',
                   query=dict_to_query({
                       '_csrfToken': csrf_token,
                       'bookId': book_id,
                       'chapterId': chapter_id,
                       '_': int(timestamp.timestamp() * 1000),
                   }))


class WebNovelComFetchStrategy(ChapterFetchStrategy, ABC):
    from lightnovel.qidianunderground_org import QidianUndergroundOrgApi
    _qidian_underground_api: QidianUndergroundOrgApi = None
    _api: LightNovelApi = None

    def __init__(self, web_novel_api: 'WebNovelComApi', qidian_underground_api: QidianUndergroundOrgApi):
        super(WebNovelComFetchStrategy, self).__init__(web_novel_api)
        self._qidian_underground_api = qidian_underground_api

    def _fetch_indexed_chapters(self, novel: Novel) -> Generator[Tuple[Book, Chapter], None, None]:
        """
        Generates all chapters from the chapter index.

        If there's no chapters generated at the end, the last chapter will be generated to allow for following
        chapter links.
        :param novel: The novel whose chapter index should be processed.
        :return: A generator of book-chapter pairs.
        """
        qu_switch = False
        # noinspection PyTypeChecker
        qu_novel: QidianUndergroundOrgNovel = None
        # noinspection PyTypeChecker
        chapter_entry: WebNovelComChapterEntry = None
        for book, chapter_entry in novel.generate_chapter_entries():
            if chapter_entry.is_vip and not qu_switch:
                qu_switch = True
                self.log.info("Encountered pay wall. Continuing to download chapters from Qidian Underground.")
            if not qu_switch and self._should_download_chapter(chapter_entry):
                self._check_blacklist(chapter_entry)
                # noinspection PyTypeChecker
                chapter: WebNovelComChapter = self._fetch_chapter(chapter_entry)
                yield book, chapter
                self._add_to_blacklist(chapter_entry)
            if qu_switch:
                self._acquire_qidian_underground_api()
                if qu_novel is None:
                    try:
                        qu_novel_entry = self._qidian_underground_api.search(novel.title)[0]
                        qu_novel = self._qidian_underground_api.get_novel(qu_novel_entry)
                    except LookupError:
                        self.log.error("Could not find novel on Qidian Underground.")
                        return
                if chapter_entry.abs_index not in qu_novel.index_to_chapter_entry:
                    self.log.error(
                        f"Qidian Underground has not yet uploaded chapter {chapter_entry.abs_index}.")
                    return
                qu_chapter_entry = qu_novel.index_to_chapter_entry[chapter_entry.abs_index]
                qu_chapter_entry.abs_index = chapter_entry.abs_index
                qu_chapter_entry.index = chapter_entry.index
                qu_chapter_entry._title = chapter_entry.title
                if self._should_download_chapter(qu_chapter_entry):
                    chapter: QidianUndergroundOrgChapter = self._qidian_underground_api.get_chapter(
                        chapter_entry.abs_index)
                    chapter.abs_index = chapter_entry.abs_index
                    chapter.index = chapter_entry.index
                    yield book, chapter
        if chapter_entry is None:
            self.log.warning("No chapters were generated from the chapter index.")
            return

    def _fetch_linked_chapters(self, last_chapter: Chapter) -> Generator[Chapter, None, None]:
        yield from ()

    def _acquire_qidian_underground_api(self):
        if not self._qidian_underground_api:
            from lightnovel.qidianunderground_org import QidianUndergroundOrgApi
            self._qidian_underground_api = QidianUndergroundOrgApi(self._api.session)


# noinspection DuplicatedCode
class AllPlusQUChapterFetchStrategy(WebNovelComFetchStrategy):
    def _should_download_chapter(self, chapter_entry: WebNovelComChapterEntry) -> bool:
        return True


class UpdatedPlusQUChapterFetchStrategy(WebNovelComFetchStrategy):
    def _should_download_chapter(self, chapter_entry: WebNovelComChapterEntry) -> bool:
        cached = self._chapter_already_downloaded(chapter_entry)
        if cached:
            self.log.debug(f"Chapter {chapter_entry} already downloaded.")
        else:
            self.log.debug(f"Chapter {chapter_entry} is new.")
        return not cached

    def _chapter_already_downloaded(self, chapter_entry: ChapterEntry) -> bool:
        adapter = self._adapter
        return isinstance(adapter, FileCacheAdapter) and adapter.would_hit(chapter_entry.spoof_url,
                                                                           {'Accept': str(chapter_entry.mime_type)})


class WebNovelComApi(WebNovelCom, LightNovelApi):
    from lightnovel.qidianunderground_org import QidianUndergroundOrgApi
    _qidian_underground_api: QidianUndergroundOrgApi = None

    @property
    def novel_url(self) -> str:
        """
        The url to the novels. Used for listing cached novels.
        """
        return self.change_url(path='/book').url

    @property
    def qidian_underground_api(self) -> QidianUndergroundOrgApi:
        return self._qidian_underground_api

    @qidian_underground_api.setter
    def qidian_underground_api(self, value: QidianUndergroundOrgApi):
        self._qidian_underground_api = value

    @property
    def fetch_all(self) -> ChapterFetchStrategy:
        return AllPlusQUChapterFetchStrategy(self, self._qidian_underground_api)

    @property
    def fetch_updated(self) -> ChapterFetchStrategy:
        return UpdatedPlusQUChapterFetchStrategy(self, self._qidian_underground_api)

    def _get_novel(self, url: Url, **kwargs) -> WebNovelComNovel:
        self.fetch_session_cookie_if_necessary()
        url = Url('https', host='www.webnovel.com', path='/'.join(url.path.lstrip('/').split('/')[:2]))
        return WebNovelComNovel(url, self._get_html_document(url, **kwargs), self._session)

    def get_chapter(self, url: Url, **kwargs: Any) -> WebNovelComChapter:
        headers = kwargs.setdefault('headers', {})
        headers.setdefault('Accept', 'application/json, text/javascript, */*; q=0.01')
        headers.setdefault('Upgrade-Insecure-Requests', None)
        headers.setdefault('X-Requested-With', 'XMLHttpRequest')
        self.fetch_session_cookie_if_necessary()
        return WebNovelComChapter(url, self._get_json_document(url, **kwargs), self._session.cookies.get('_csrfToken'))

    def search(self, keyword: str = '') -> List[WebNovelComNovelEntry]:
        """Searches for novels matching certain criteria.

        :param keyword: The keyword to search for.
        :return: A list of matched novels (:class:`WebNovelSearchEntry`) and the amount of total novels that matched the search criteria.
        """
        self.fetch_session_cookie_if_necessary()
        if isinstance(self.adapter, FileCacheAdapter):
            self.adapter.use_cache = False
        data = [
            ('_csrfToken', self._session.cookies.get('_csrfToken')),
            ('keywords', keyword)
        ]
        # These cookies aren't needed, but makes spoofing more believable
        self._session.cookies.set_cookie(create_cookie('e1', '{"pid":"qi_p_home","eid":"qi_A02","l1":"99"}',
                                                       domain='.webnovel.com', path='/'))
        # noinspection SpellCheckingInspection
        self._session.cookies.set_cookie(create_cookie('e2', '',
                                                       # '{"pid":"qi_p_googleonetap","eid":"qi_I01","l1":1}',
                                                       domain='.webnovel.com', path='/'))
        response = self._session.post("https://www.webnovel.com/go/pcm/search/autoComplete", headers={
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Upgrade-Insecure-Requests': None,
            'X-Requested-With': 'XMLHttpRequest',
        }, data=encode_form_data(data).replace('+', ' '))
        if isinstance(self.adapter, FileCacheAdapter):
            self.adapter.use_cache = True
        if len(response.text) == 0:
            self.log.error("Api did not return anything")
            return []
        data = response.json()
        if data['msg'] != 'Success':
            self.log.error(f"Api returned error {data['code']}: {data['msg']}")
            return []
        entries = []
        for item in data.get('data', {}).get('searchAssociationItems', []):
            if item['type'] == 0:
                entries.append(WebNovelComNovelEntry(item))
        return entries

    def search_for_specific_title(self, title: str) -> List[WebNovelComNovelEntry]:
        title_len = len(title)
        starting_length = 7
        min_length = 2
        max_length = 25
        search_from1 = min(starting_length, title_len)
        search_to1 = min(title_len, max_length)
        search_from2 = min(min_length, title_len)
        search_to2 = search_from1 - 1
        search_lengths = list(range(search_from1, search_to1 + 1)) + list(range(search_from2, search_to2 + 1))
        searched_lengths = []
        old_delay = self._session.request_timeout
        self._session.request_timeout = timedelta(seconds=0.5)  # manual search requests go all the way down to ~250ms
        for length in search_lengths:
            keyword = title[:length].lower()
            if len(keyword) in searched_lengths:
                continue
            searched_lengths.append(len(keyword))
            matches = self._search_using_keyword(keyword, title)
            if len(matches) == 0:
                continue
            self._session.request_timeout = old_delay
            return matches
        self.log.error(f"Could not find any novel matching '{title}'.")
        self._session.request_timeout = old_delay
        return []

    def _search_using_keyword(self, keyword: str, title: str) -> List[WebNovelComNovelEntry]:
        lst = self.search(keyword)
        if len(lst) == 0:
            self.log.debug(f"Could not find any novel when searching for '{keyword}' ({title}).")
            return []
        else:
            match_list = list(filter(lambda n:
                                     re.sub(r"\W+", ' ', n.title).strip().lower() ==
                                     re.sub(r"\W+", ' ', title).strip().lower(), lst))
            if len(match_list) == 0:
                self.log.debug(f"Could not find exact match for '{title}' when searching for '{keyword}'.")
                return []
            else:
                self.log.info(f"Found '{title}'.")
                return match_list

    def fetch_session_cookie_if_necessary(self):
        if not self._session.cookies.get('_csrfToken'):
            if isinstance(self.adapter, FileCacheAdapter):
                self.adapter.use_cache = False
            url = 'https://www.webnovel.com'
            if isinstance(self._session, Browser):
                response = self._session.navigate(url)
            else:
                response = self._session.get(url)
            if isinstance(self.adapter, FileCacheAdapter):
                self.adapter.use_cache = True
            response.raise_for_status()
