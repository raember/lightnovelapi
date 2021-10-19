import html
import json
import re
from datetime import datetime
from enum import Enum
from typing import List, Tuple

from bs4 import BeautifulSoup
from bs4.element import Tag, NavigableString
from spoofbot import Browser
from spoofbot.adapter import FileCacheAdapter
from spoofbot.util import encode_form_data
from urllib3.util.url import parse_url, Url

from lightnovel import ChapterEntry, Book, Novel, Chapter, LightNovelApi, NovelEntry
from util.text import normalize_string


class WuxiaWorldCom:
    _hoster_base_url: Url = parse_url('https://www.wuxiaworld.com')
    _hoster_name: str = 'WuxiaWorld'
    _hoster_short_name: str = 'WW'


class WuxiaWorldComChapterEntry(WuxiaWorldCom, ChapterEntry):
    def _create_chapter_entry_from_url(self, url: Url) -> 'WuxiaWorldComChapterEntry':
        return WuxiaWorldComChapterEntry(url)


class WuxiaWorldComBook(WuxiaWorldCom, Book):
    _chapter_entries: List[WuxiaWorldComChapterEntry] = []


class Status(Enum):
    ANY = None
    ONGOING = True
    COMPLETED = False

    @classmethod
    def from_int(cls, status: int):
        if status == 1:
            return cls.ONGOING
        elif status == 2:
            return cls.COMPLETED
        return cls.ANY


class NovelTag(Enum):
    CHINESE = 'Chinese'
    COMPLETED = 'Completed'
    COMPLETED_RECS = 'Completed Recs'
    KOREAN = 'Korean'
    ONGOING = 'Ongoing'
    ORIGINAL = 'Original'

    @classmethod
    def from_str(cls, tag: str):
        for member in cls:
            if tag == member.value:
                return member


class Genre(Enum):
    ACTION = 'Action'
    ALCHEMY = 'Alchemy'
    COMEDY = 'Comedy'
    COOKING = 'Cooking'
    CRAFTING = 'Crafting'
    FANTASY = 'Fantasy'
    KINGDOM_BUILDING = 'Kingdom Building'
    MATURE = 'Mature'
    MODERN_SETTING = 'Modern Setting'
    MYSTERY = 'Mystery'
    POLITICAL_INTRIGUE = 'Political Intrigue'
    POST_APOCALYPTIC = 'Post-apocalyptic'
    ROMANCE = 'Romance'
    SUPERPOWERS = 'Superpowers'
    TRAGEDY = 'Tragedy'
    VIRTUAL_REALITY = 'Virtual Reality'
    WUXIA = 'Wuxia'
    XIANXIA = 'Xianxia'
    XUANHUAN = 'Xuanhuan'

    @classmethod
    def from_str(cls, tag: str):
        for member in cls:
            if tag == member.value:
                return member


class SortType(Enum):
    NAME = 'Name'
    POPULAR = 'Popular'
    CHAPTERS = 'Chapters'
    NEW = 'New'


class WuxiaWorldComNovelEntry(WuxiaWorldCom, NovelEntry):
    id: int
    slug: str
    cover_url: str
    abbreviation: str
    synopsis: Tag
    language: str
    time_created: datetime
    sneakPeek: bool
    status: Status
    chapter_count: int
    tags: List[NovelTag]
    genres: List[Genre]

    def __init__(self, json_data: dict):
        super().__init__(Url('https', host='www.wuxiaworld.com'), json_data['name'])
        self.id = int(json_data['id'])
        self.slug = json_data['slug']
        self.cover_url = json_data['coverUrl']
        self.abbreviation = json_data['abbreviation']
        self.synopsis = BeautifulSoup(json_data['synopsis'], features="html5lib")
        self.language = json_data['language']
        self.time_created = datetime.utcfromtimestamp(float(json_data['timeCreated']))
        self.sneakPeek = bool(json_data['sneakPeek'])
        if self.sneakPeek:
            self._url = self.change_url(path=f"preview/{self.slug}")
        else:
            self._url = self.change_url(path=f"novel/{self.slug}")
        self.status = Status.from_int(json_data['status'])
        self.chapter_count = int(json_data['chapterCount'])
        self.tags = list(map(lambda tag: NovelTag.from_str(tag), json_data['tags']))
        self.genres = list(map(lambda genre: Genre.from_str(genre), json_data['genres']))


class WuxiaWorldComNovel(WuxiaWorldCom, Novel):
    _books: List[WuxiaWorldComBook]
    _karma_active: bool = False

    @property
    def karma_active(self) -> bool:
        return self._karma_active

    def _parse(self) -> bool:
        head = self.document.content.select_one('head')
        if not isinstance(head, Tag):
            raise Exception("Unexpected type of tag selection")
        meta_description = head.select_one('meta[name="description"]')
        if not isinstance(meta_description, Tag):
            raise Exception("Unexpected type of tag selection")
        if not meta_description.has_attr('content'):
            return False
        head_json = head.select_one('script[type="application/ld+json"]')
        if not isinstance(head_json, Tag):
            raise Exception("Unexpected type of tag selection")
        json_data = json.loads(head_json.text)
        self._title = json_data['name']
        self.log.debug(f"Novel title is: {self._title}")
        url = json_data['potentialAction']['target'].get('urlTemplate', '')
        if url == '':
            return False
        description_list = self.document.content.select_one('div.novel-body')
        if not isinstance(description_list, Tag):
            raise Exception("Unexpected type of tag selection")
        descriptions = re.sub(r'\n+', '\n', description_list.text).strip('\n').split('\n')
        self._translators = []
        while len(descriptions) > 0:
            if descriptions[0].strip() == "Translator:":
                descriptions.pop(0)
                self._translators.append(descriptions.pop(0))
                self.log.debug(f"Got translator: {self._translators[-1]}")
            elif descriptions[0].strip() == "Author:":
                descriptions.pop(0)
                self._author = descriptions.pop(0)
                self.log.debug(f"Got author: {self._author}")
                break
            else:
                self.log.debug(f"Discarding description entry '{descriptions.pop(0)}'")
        # self._author = dl.contents[7].text
        # self._translator = dl.contents[3].text  # json_data['author']['name']
        legal_paragraph = self.document.content.select_one('p.legal')
        if not isinstance(legal_paragraph, Tag):
            raise Exception("Unexpected type of tag selection")
        self._rights = html.unescape(legal_paragraph.getText())
        self._release_date = datetime.fromisoformat(json_data['datePublished'])
        for tag in head.select('script[type="text/javascript"]'):
            if "karmaActive" in tag.text:
                self._karma_active = '"karmaActive":true' in tag.text
        if self._karma_active:
            self.log.warning("This novel might require karma points to unlock chapters.")
        meta_image = head.select_one('meta[property="og:image"]')
        if not isinstance(meta_image, Tag):
            raise Exception("Unexpected type of tag selection")
        self._cover_url = parse_url(meta_image.get('content'))
        p15 = self.document.content.select_one('div.p-15')
        if not isinstance(p15, Tag):
            raise Exception("Unexpected type of tag selection")
        self._tags = self.__extract_tags()
        self._description = p15.select('div.fr-view')[1]
        self._books = self.__extract_books(p15)
        self._language = 'en'
        return True

    def __extract_tags(self) -> List[str]:
        tags = []
        for tag_html in self.document.content.select('div.genres a'):
            tag = tag_html.text.strip()
            tags.append(tag)
        self.log.debug(f"Tags found: {tags}")
        return tags

    def __extract_books(self, p15: Tag) -> List[WuxiaWorldComBook]:
        already_processed_urls = []
        books = []
        book_index = 0
        for book_html in p15.select('div#accordion div.panel.panel-default'):
            book_index += 1
            book = WuxiaWorldComBook(book_html.select_one('a.collapsed').text.strip())
            book.novel = self
            book.index = book_index
            book._chapter_entries = self.__extract_chapters(book_html, already_processed_urls)
            self.log.debug(f"Book: {book}")
            books.append(book)
        return books

    def __extract_chapters(self, book_html: Tag, already_processed_urls: list) -> List[WuxiaWorldComChapterEntry]:
        chapters = []
        chapter_index = 0
        for chapter_html in book_html.select('div div li a'):
            url = Url('https', host='www.wuxiaworld.com', path=chapter_html.get('href'))
            if url in already_processed_urls:
                self.log.debug(f"Found duplicate chapter URL: {url}")
                continue
            already_processed_urls.append(url)
            chapter_index += 1
            chapter = WuxiaWorldComChapterEntry(url, title=chapter_html.text.strip())
            chapter.index = chapter_index
            chapters.append(chapter)
        self.log.debug(f"Chapters found: {len(chapters)}")
        return chapters


class WuxiaWorldComChapter(WuxiaWorldCom, Chapter):
    _chapter_id: int
    _is_teaser: bool
    _karma_locked: bool

    @property
    def chapter_id(self) -> int:
        return self._chapter_id

    @property
    def is_teaser(self) -> bool:
        return self._is_teaser

    @property
    def karma_locked(self) -> bool:
        return self._karma_locked

    def _parse(self) -> bool:
        head = self.document.content.select_one('head')
        if not isinstance(head, Tag):
            raise Exception("Unexpected type of tag selection")
        link = head.select_one('link[rel="canonical"]')
        if not isinstance(link, Tag):
            raise Exception("Unexpected type of tag selection")
        url = parse_url(link.get('href'))
        if url.path.startswith('/preview') or url.path.startswith('/Error'):
            return False
        self._karma_locked = False  # For is_complete() to run smoothly
        self._is_teaser = False  # For is_complete() to run smoothly
        if self.is_complete():
            json_data = None
            for script_tag in head.select('script'):
                script = script_tag.text.strip('\n \t;')
                if script.startswith('var CHAPTER = '):
                    json_data = json.loads(script[14:])
                    break
            if json_data is None:
                return False
            self._title = json_data['name']
            self._chapter_id = int(json_data.get('id', 0))
            self._is_teaser = json_data.get('isTeaser', False)
            if self.is_teaser:
                self.log.warning("Chapter is a teaser")
            if json_data.get('prevChapter', '') != '':
                self._previous_chapter = self.change_url(path=json_data['prevChapter'])
            if json_data.get('nextChapter', '') != '':
                self._next_chapter = self.change_url(path=json_data['nextChapter'])
            if self._title == '':
                self.log.warning("Couldn't extract data from CHAPTER variable.")
            self._karma_locked = self._is_karma_locked()
            if self._karma_locked:
                self.log.warning("This chapter requires karma points to unlock.")
                return False
            content = self.document.content.select_one('div.p-15 div.fr-view')
            if content is None:
                content = self.document.content.select_one('div.fr-view')
            if not isinstance(content, Tag):
                raise Exception("Unexpected type of tag selection")
            del content['class']
            self._content = content
            return True
        return False

    def _create_chapter_entry_from_url(self, url: Url) -> 'WuxiaWorldComChapterEntry':
        return WuxiaWorldComChapterEntry(url)

    def is_complete(self) -> bool:
        meta_description = self.document.content.select_one('head meta[name="description"]')
        if not isinstance(meta_description, Tag):
            raise Exception("Unexpected type of description meta data")
        return meta_description.has_attr('content') and not self.karma_locked and not self.is_teaser

    def _is_karma_locked(self) -> bool:
        return self.document.content.select_one('span.badge') is not None

    def clean_content(self):
        bs = BeautifulSoup(features="html5lib")
        new_content = bs.new_tag('div')
        new_content.clear()
        tags_cnt = 0
        max_tags_cnt = 4
        for child in self._content.children:
            if isinstance(child, NavigableString):
                if len(child.strip('\n  ')) == 0:
                    # self.log.debug("Empty string.")
                    pass
                else:
                    self.log.warning(f"Non-Empty string: '{child}'.")
            elif isinstance(child, Tag):
                # ['p', 'div', 'a', 'blockquote', 'ol', 'ul', 'h1', 'h2', 'h3', 'h4', 'h5']
                if child.name == 'blockquote':  # Block quotes have to have a paragraph within
                    p = bs.new_tag('p')
                    for children in child.children:
                        p.append(children)
                    child.clear()
                    child.append(p)
                if child.name in ['p', 'div', 'blockquote']:
                    #     child.name = 'p'
                    # if child.name == 'p':
                    if len(child.text.strip('\n ')) == 0:
                        # self.log.debug("Empty paragraph.")
                        pass
                    else:
                        for desc in child.descendants:
                            if isinstance(desc, Tag):
                                from lightnovel import EpubMaker
                                if desc.name not in EpubMaker.ALLOWED_TAGS:
                                    self.log.debug(f"Tag '{desc.name}' is not allowed in an epub. Changing to span")
                                    desc.name = 'span'
                                if desc.name == 'a':
                                    self.log.debug(f"Cleaning link '{desc}'")
                                    desc.attrs = {}
                        if child.text in ['Next Chapter', 'Previous Chapter']:
                            continue
                        new_content.append(child.__copy__())
                        tags_cnt += 1
                        title_str = re.sub(r'[^a-z\s\d]\s?', '', normalize_string(self._title.lower()))
                        text_start = re.sub(r'[^a-z\s\d]\s?', '',
                                            normalize_string(child.text.strip('\n ')[:len(title_str) + 20].lower()))
                        if tags_cnt <= max_tags_cnt \
                                and title_str != '' \
                                and title_str in text_start:
                            self.log.debug("Title found in paragraph. Discarding previous paragraphs.")
                            new_content.clear()
                            tags_cnt = max_tags_cnt
                elif child.name == 'hr':
                    new_content.append(child)
                elif child.name in ('a', 'script'):
                    continue
                elif child.name in ['ol', 'ul']:
                    new_content.append(child)
                else:
                    raise Exception(f"Unexpected tag name: {child}")
            else:
                raise Exception(f"Unexpected type: {child}")
        self._content = new_content

    def __clean_paragraph(self, p: Tag):
        for desc in p.descendants:
            if desc.name is None:
                continue
            from lightnovel import EpubMaker
            if desc.name not in EpubMaker.ALLOWED_TAGS:
                self.log.debug(f"Tag '{desc.name}' is not allowed in an epub. Changing to span")
                desc.name = 'span'
            if desc.name == 'a':
                self.log.debug(f"Cleaning link '{desc['href']}'")
                desc.attrs = {}


class WuxiaWorldComApi(WuxiaWorldCom, LightNovelApi):

    @property
    def novel_url(self) -> str:
        """
        The url to the novels. Used for listing cached novels.
        """
        return self.change_url(path='/novel').url

    def _get_novel(self, url: Url, **kwargs) -> WuxiaWorldComNovel:
        return WuxiaWorldComNovel(url, self._get_html_document(url))

    def get_chapter(self, url: Url, **kwargs) -> WuxiaWorldComChapter:
        return WuxiaWorldComChapter(url, self._get_html_document(url))

    # TODO: Respect robots.txt and don't use /api/* calls. Instead, use https://www.wuxiaworld.com/sitemap/novels
    def search(
            self,
            title: str = '',
            tags: Tuple[NovelTag] = (),
            genres: Tuple[Genre] = (),
            status: Status = Status.ANY,
            sort_by: SortType = SortType.NAME,
            sort_asc: bool = True,
            search_after: int = None,
            count: int = 15) -> List[WuxiaWorldComNovelEntry]:
        """Searches for novels matching certain criteria. Violates robots.txt

        :param title: The title or abbreviation to search for.
        :param tags: The tags(:class:`NovelTag`) which the novels must have.
        :param genres: The genres(:class:`Genre`) which the novels must have.
        :param status: The :class:`Status` of the novel.
        :param sort_by: What criteria to sort by.
        :param sort_asc: Whether to sort in an ascending order or not.
        :param search_after: The index after which to return the list. Useful if the first request did not return all matches.
        :param count: How many matches to maximally include in the returned list.
        :return: A list of matched novels (:class:`WuxiaWorldSearchEntry`) and the amount of total novels that matched the search criteria.
        """
        self.log.warning("This method violates robots.txt.")
        self.fetch_session_cookie_if_necessary()
        if isinstance(self.adapter, FileCacheAdapter):
            self.adapter.use_cache = False
        response = self._session.post("https://www.wuxiaworld.com/api/novels/search", headers={
            'Accept': 'application/json, text/plain, */*',
            'Content-Type': 'application/json;charset=utf-8',
            'Upgrade-Insecure-Requests': None,
        }, data=json.dumps({
            "title": title,
            "tags": list(map(lambda tag: tag.value, tags)),
            "genres": list(map(lambda genre: genre.value, genres)),
            "active": status.value,
            "sortType": sort_by.value,
            "sortAsc": sort_asc,
            "searchAfter": search_after,
            "count": count,
        }, separators=(',', ':')))
        if isinstance(self.adapter, FileCacheAdapter):
            self.adapter.use_cache = True
        data = response.json()
        assert data['result']
        entries = []
        for item in data['items']:
            entries.append(WuxiaWorldComNovelEntry(item))
        return entries

    def fetch_session_cookie_if_necessary(self):
        if not self._session.cookies.get('__cfduid'):
            if isinstance(self.adapter, FileCacheAdapter):
                self.adapter.use_cache = False
            url = 'https://www.wuxiaworld.com'
            if isinstance(self._session, Browser):
                response = self._session.navigate(url)
            else:
                response = self._session.get(url)
            if isinstance(self.adapter, FileCacheAdapter):
                self.adapter.use_cache = True
            response.raise_for_status()

    def login(self, email: str, password: str, remember: bool = False) -> bool:
        """Logs a user in to use during the api use.
        Cam be used to earn daily karma or spend said karma on chapters.

        :param email: The email to log in with.
        :param password: The password for the account.
        :param remember: The "Remember me" checkbox.
        :return: True if the login succeeded, otherwise False.
        """
        self.fetch_session_cookie_if_necessary()
        if isinstance(self.adapter, FileCacheAdapter):
            self.adapter.use_cache = False
        login_page = self._get_html_document(parse_url("https://www.wuxiaworld.com/account/login"))
        rvt_input = login_page.content.select_one('input[name="__RequestVerificationToken"]')
        if not isinstance(rvt_input, Tag):
            raise Exception("Unexpected type of request verification token")
        data = [
            ('Email', email),
            ('Password', password),
            ('RememberMe', 'true' if remember else 'false'),
            ('__RequestVerificationToken', rvt_input.get('value')),
            ('RememberMe', 'false')
        ]
        response = self._session.post('https://www.wuxiaworld.com/account/login', headers={
            'Content-Type': 'application/x-www-form-urlencoded'
        }, data=encode_form_data(data))
        if isinstance(self.adapter, FileCacheAdapter):
            self.adapter.use_cache = True
        response.raise_for_status()
        return 200 <= response.status_code < 300

    def logout(self) -> bool:
        """Logs a user out.

        :return: True if the logout succeeded, otherwise False.
        """
        self.fetch_session_cookie_if_necessary()
        response = self._session.post('https://www.wuxiaworld.com/account/logout', headers={
            'Accept': 'application/json, text/plain, */*',
            'Upgrade-Insecure-Requests': None,
        }, data='')
        response.raise_for_status()
        return 200 <= response.status_code < 300

    def get_karma(self) -> Tuple[int, int]:
        """Updates the karma statistics of the logged in user.

        :return: A tuple of the karma (normal and gold karma)
        """
        self.fetch_session_cookie_if_necessary()
        if isinstance(self.adapter, FileCacheAdapter):
            self.adapter.use_cache = False
        karma_page = self._get_html_document(parse_url("https://www.wuxiaworld.com/profile/karma"))
        if isinstance(self.adapter, FileCacheAdapter):
            self.adapter.use_cache = True
        karma_table = karma_page.content.select_one("div.table-responsive table tbody")
        if not isinstance(karma_table, Tag):
            raise Exception("Unexpected type of table query")
        karma_table_rows = karma_table.select("tr")
        regular_karma = self._get_karma_from_table_row(karma_table_rows[0])
        gold_karma = self._get_karma_from_table_row(karma_table_rows[1])
        return regular_karma, gold_karma

    @staticmethod
    def _get_karma_from_table_row(row: Tag) -> int:
        return int(row.select("td")[1].text)

    def claim_daily_karma(self) -> bool:
        self.fetch_session_cookie_if_necessary()
        if isinstance(self.adapter, FileCacheAdapter):
            self.adapter.use_cache = False
        mission_page = self._get_html_document(parse_url("https://www.wuxiaworld.com/profile/missions"))
        if isinstance(self.adapter, FileCacheAdapter):
            self.adapter.use_cache = True
        rvt_input = mission_page.content.select_one('input[name="__RequestVerificationToken"]')
        if not isinstance(rvt_input, Tag):
            raise Exception("Unexpected type of request verification token")
        if not rvt_input:
            return False
        data = [
            ('Type', 'Login'),
            ('__RequestVerificationToken', rvt_input.get('value')),
        ]
        response = self._session.post('https://www.wuxiaworld.com/profile/missions', headers={
            'Content-Type': 'application/x-www-form-urlencoded'
        }, data=encode_form_data(data))
        response.raise_for_status()
        return 200 <= response.status_code < 300
