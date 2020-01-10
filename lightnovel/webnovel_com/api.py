import html
import json
import re
from datetime import datetime
from typing import List, Generator, Tuple

from bs4 import BeautifulSoup
from bs4.element import Tag
from spoofbot import Browser
from spoofbot.adapter import CacheAdapter
from spoofbot.util import encode_form_data
from urllib3.util.url import parse_url, Url

from lightnovel import ChapterEntry, Book, Novel, Chapter, LightNovelApi, SearchEntry
from util.other import query_to_dict


def unescape_string(string: str) -> str:
    return string.encode('utf8').decode('unicode-escape')


class WebNovelCom:
    _hostname = 'www.webnovel.com'


class WebNovelComChapterEntry(WebNovelCom, ChapterEntry):
    _is_vip: int

    def __init__(self, url: Url, title: str, is_vip: int):
        super(WebNovelComChapterEntry, self).__init__(url, title)
        self._is_vip = is_vip

    @property
    def is_vip(self) -> bool:
        return self._is_vip == 2


class WebNovelComBook(WebNovelCom, Book):
    _chapter_entries: List[WebNovelComChapterEntry] = []
    _chapters: List['WebNovelComChapter'] = []


class WebNovelComSearchEntry(WebNovelCom, SearchEntry):
    id: int

    def __init__(self, json_data: dict):
        super().__init__(Url('https', host='www.webnovel.com', path='/book'))
        self.id = int(json_data['id'])
        self.title = json_data['name']
        self._url = self.alter_url(f"book/{self.id}")


class WebNovelComNovel(WebNovelCom, Novel):
    _books: List[WebNovelComBook]
    _browser: Browser
    _novel_id: int
    _timestamp: datetime

    def __init__(self, url: Url, document: BeautifulSoup, browser: Browser):
        super(WebNovelComNovel, self).__init__(url, document)
        self._browser = browser
        self._novel_id = 0
        self._timestamp = datetime.now()

    @property
    def novel_id(self) -> int:
        return self._novel_id

    @property
    def timestamp(self) -> datetime:
        return self._timestamp

    @timestamp.setter
    def timestamp(self, value: datetime):
        self._timestamp = value

    def parse(self) -> bool:
        head = self._document.select_one('head')
        if not isinstance(head, Tag):
            raise Exception("Unexpected type of tag selection")
        # meta_image = head.select_one('meta[property="og:image"]')
        # if not isinstance(meta_image, Tag):
        #     raise Exception("Unexpected type of tag selection")
        # self._cover_url = meta_image.get('content')
        url = head.select_one('meta[property="og:url"]')
        if not isinstance(url, Tag):
            raise Exception("Unexpected type of tag selection")
        self._novel_id = int(parse_url(url.get('content')).query.split('=')[1])
        description = head.select_one('meta[property="og:description"]')
        if not isinstance(description, Tag):
            raise Exception("Unexpected type of tag selection")
        self._description = self._document.new_tag('p')
        self._description.string = html.unescape(description.get('content'))
        rights = self._document.select_one('p.g_ft_copy')
        if not isinstance(rights, Tag):
            raise Exception("Unexpected type of tag selection")
        self._rights = html.unescape(rights.text)
        g_data = self._document.select_one('body.footer_auto > script')
        if not isinstance(g_data, Tag):
            raise Exception("Unexpected type of tag selection")
        match = re.search(r"g_data\.book = (?P<json>{.*\});$", g_data.text, re.MULTILINE)
        if not match:
            raise Exception("Failed to match for json data")
        json_str = match.group('json')
        json_str = json_str.replace(r'\ ', ' ').replace(r"\'", "'").replace(r"\>", ">")
        json_data = json.loads(json_str)['bookInfo']
        self._language = 'en'
        self._author = json_data['authorName']
        translators = json_data.get('translatorItems', [])
        if translators is not None and len(translators) > 0:
            self._translator = translators[0]['name']
        else:
            self._translator = ''
        cover_update_time = datetime.fromtimestamp(float(json_data['coverUpdateTime']) / 1000)
        self._cover_url = f'https://img.webnovel.com/bookcover/{self._novel_id}/300/300.jpg' \
                          f'?coverUpdateTime={int(cover_update_time.timestamp() * 1000)}'
        self._tags = list(map(lambda i: i['tagName'], json_data['tagInfo']['popularItems']))
        self._release_date = datetime.fromtimestamp(0)

        adapter = self._browser.session.get_adapter('https://')
        if isinstance(adapter, CacheAdapter):
            adapter.next_request_cache_url = parse_url(
                f"https://www.webnovel.com/apiajax/chapter/{self._novel_id}.html"
            )
        # noinspection SpellCheckingInspection
        chapter_list_url = Url('https', host='www.webnovel.com', path='/apiajax/chapter/GetChapterList')
        response = self._browser.get(chapter_list_url.url, params={
            '_csrfToken': self._browser.session.cookies.get('_csrfToken'),
            'bookId': self._novel_id,
            '_': int(self._timestamp.timestamp() * 1000),
        })
        json_data = response.json()['data']
        book_info = json_data['bookInfo']
        self._title = book_info['bookName']
        self._books = self.__extract_books(json_data['volumeItems'])
        first_chapter = self._books[0].chapter_entries[0]
        self._first_chapter_path = f"{first_chapter.url.path}?{first_chapter.url.query}"
        self._success = True
        return True

    def __extract_books(self, volume_items: List[dict]) -> List[WebNovelComBook]:
        books = []
        book_index = 0
        for volume in volume_items:
            book_index += 1
            if volume['name'] == '':
                del volume['name']
            book = WebNovelComBook(volume.get('name', f'Volume {book_index}'))
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
                WebNovelComChapter.build_url(
                    self._browser.session.cookies.get('_csrfToken'),
                    self._novel_id,
                    chapter_item['id'],
                    self._timestamp,
                ),
                title=chapter_item['name'],
                is_vip=int(chapter_item['isVip']),
            )
            chapter.index = chapter_index
            chapters.append(chapter)
        self.log.debug(f"Chapters found: {len(chapters)}")
        return chapters


class WebNovelComChapter(WebNovelCom, Chapter):
    _document: dict
    _csrf_token: str
    _chapter_id: int
    _is_vip: int
    _timestamp: datetime

    def __init__(self, url: Url, json_data: dict, csrf_token: str):
        # noinspection PyTypeChecker
        super(WebNovelComChapter, self).__init__(url, json_data)
        self._csrf_token = csrf_token
        self._timestamp = datetime.now()

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

    def parse(self) -> bool:
        data = self._document['data']
        book_info = data['bookInfo']
        self._language = book_info['languageName']
        self._author = book_info['authorName']
        translators = book_info.get('translatorItems', [])
        if translators is not None and len(translators) > 0:
            self._translator = translators[0]['name']
        else:
            self._translator = ''
        chapter_info = data['chapterInfo']
        self._chapter_id = int(chapter_info['chapterId'])
        self._title = chapter_info['chapterName']
        self._is_vip = int(chapter_info['isVip'])
        previous_chapter_url = self.build_url(
            self._csrf_token,
            int(book_info['bookId']),
            chapter_info['preChapterId'],
            self._timestamp,
        )
        self._previous_chapter_path = f"{previous_chapter_url.path}?{previous_chapter_url.query}"
        next_chapter_url = self.build_url(
            self._csrf_token,
            int(book_info['bookId']),
            chapter_info['nextChapterId'],
            self._timestamp,
        )
        self._next_chapter_path = f"{next_chapter_url.path}?{next_chapter_url.query}"
        doc = BeautifulSoup('html', features="html5lib")
        self._content = doc.new_tag('div')
        for paragraph in chapter_info['contents']:
            p = doc.new_tag('p')
            # paragraph['content'].encode('latin1').decode('unicode_escape').encode('latin1').decode('utf8')
            content: str = paragraph['content']
            p.string = re.sub(r"<pirate>.*?</pirate>", '', content)
            self._content.append(p)
        self._success = True
        return True

    def is_complete(self) -> bool:
        # Because the pipeline checks for this and we want to continue to Qidian Underground
        return True  # not self.is_vip

    def clean_content(self):
        pass

    @staticmethod
    def build_url(csrf_token: str, book_id: int, chapter_id: int, timestamp: datetime = datetime.now()) -> Url:
        # noinspection SpellCheckingInspection
        return Url('https', host='www.webnovel.com', path='/apiajax/chapter/GetContent',
                   query='&'.join([f"{k}={v}" for k, v in {
                       '_csrfToken': csrf_token,
                       'bookId': book_id,
                       'chapterId': chapter_id,
                       '_': int(timestamp.timestamp() * 1000),
                   }.items()]))


class WebNovelComApi(WebNovelCom, LightNovelApi):
    def get_novel(self, url: Url) -> WebNovelComNovel:
        self.fetch_session_cookie_if_necessary()
        return WebNovelComNovel(url, self._get_document(url), self._browser)

    def get_chapter(self, url: Url) -> WebNovelComChapter:
        if isinstance(self.adapter, CacheAdapter):
            query = query_to_dict(url.query)
            self.adapter.next_request_cache_url = parse_url(
                f"https://www.webnovel.com/apiajax/chapter/{query['bookId']}/{query['chapterId']}.html"
            )
        self.fetch_session_cookie_if_necessary()
        self.check_wait_condition()
        response = self._browser.navigate(url.url, headers={
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Upgrade-Insecure-Requests': None,
            'X-Requested-With': 'XMLHttpRequest',
        })
        self._last_request_timestamp = datetime.now()
        response.encoding = None  # Figure out correct encoding yourself
        return WebNovelComChapter(url, response.json(), self._browser.session.cookies.get('_csrfToken'))

    def search(self, keyword: str = '') -> List[WebNovelComSearchEntry]:
        """Searches for novels matching certain criteria.

        :param keyword: The keyword to search for.
        :return: A list of matched novels (:class:`WebNovelSearchEntry`) and the amount of total novels that matched the search criteria.
        """
        self.fetch_session_cookie_if_necessary()
        self.check_wait_condition()
        if isinstance(self.adapter, CacheAdapter):
            self.adapter.use_cache = False
        data = [
            ('_csrfToken', self._browser.session.cookies.get('_csrfToken')),
            ('keyword', keyword)
        ]
        response = self._browser.post("https://www.webnovel.com/apiajax/search/AutoCompleteAjax", headers={
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Upgrade-Insecure-Requests': None,
            'X-Requested-With': 'XMLHttpRequest',
        }, data=encode_form_data(data))
        if isinstance(self.adapter, CacheAdapter):
            self.adapter.use_cache = True
        self._last_request_timestamp = datetime.now()
        data = response.json()
        assert data['msg'] == 'Success'
        entries = []
        for item in data['data'].get('books', []):
            entries.append(WebNovelComSearchEntry(item))
        return entries

    def fetch_session_cookie_if_necessary(self):
        if not self._browser.session.cookies.get('_csrfToken'):
            self.check_wait_condition()
            if isinstance(self.adapter, CacheAdapter):
                self.adapter.use_cache = False
            self._browser.navigate('https://www.webnovel.com')
            if isinstance(self.adapter, CacheAdapter):
                self.adapter.use_cache = True
        # assert self._browser.session.cookies.get('__cfduid')  # Messes up tests with cache that don't store headers

    def get_all_chapters(self, novel: WebNovelComNovel) -> Generator[Tuple[Book, Chapter], None, None]:
        """
        Creates a generator that downloads all the available chapters of a novel, including
        those that aren't listed on the front page of the novel.

        The generator can be fed into various pipelines.
        :param novel: The novel from which the chapters should be downloaded. Has to be parsed already.
        :return: A generator that downloads each chapter.
        """
        book = None
        for book, chapter_entry in novel.enumerate_chapter_entries():
            chapter = self.get_chapter(chapter_entry.url)
            chapter.index = chapter_entry.index
            yield book, chapter
            if not chapter.success:
                raise Exception("Cannot decide whether to continue because pay wall cannot be detected")
            if chapter.is_vip:
                break
        self.log.info("Continuing downloading chapters from Qidian Underground.")
        from qidianunderground_org import QidianUndergroundOrgApi
        api = QidianUndergroundOrgApi(self.browser)
        qidian_novel = api.get_novel(novel.title)
        try:
            qidian_novel.parse()
        except LookupError:
            self.log.error("Could not find novel on Qidian Underground.")
            return
        for index in qidian_novel.index_to_chapter_entry.keys():
            chapter = api.get_chapter(index)
            chapter.index = index
            yield book, chapter
