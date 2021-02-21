import logging
import re
from abc import ABC
from datetime import datetime
from io import BytesIO
from typing import List, Any, Tuple, Generator, Optional, Set, Dict

from PIL import Image
from bs4 import BeautifulSoup
from bs4.element import Tag
from requests import Session
from requests.adapters import BaseAdapter
from spoofbot import Browser, MimeTypeTag
from spoofbot.adapter import FileCacheAdapter, HarAdapter
from spoofbot.util import are_schemelessly_same_site
from urllib3.util import Url

UNKNOWN = '<unknown>'


class LoopingListError(Exception):

    def __init__(self, chapter_entry: 'ChapterEntry'):
        super().__init__(f"The chapter has already been processed before: '{chapter_entry}'")


class ParseError(Exception):
    chapter: 'Chapter'

    def __init__(self, chapter: 'Chapter'):
        super().__init__(f"Failed to parse chapter {chapter}.")
        self.chapter = chapter


class Hosted:
    _hoster_homepage: Url = None
    _hoster: str = UNKNOWN
    _hoster_abbreviation: str = UNKNOWN

    @property
    def hoster_homepage(self) -> Optional[Url]:
        """
        The url to the hoster's home page

        Inheriting classes should set this value internally.
        """
        return self._hoster_homepage

    @property
    def hoster(self) -> str:
        """
        The name of the hoster.

        Inheriting classes should set this value internally.
        """
        return self._hoster

    @property
    def hoster_abbreviation(self) -> str:
        """
        A short representation of the hosters name

        Inheriting classes should set this value internally.
        """
        return self._hoster_abbreviation

    def __str__(self):
        return self.hoster


class Logged:
    log: logging.Logger = None

    def __init__(self):
        self.log = logging.getLogger(self.__class__.__name__)


class LightNovelEntity(Hosted, Logged):
    """An entity that is identified by a url"""
    _url: Url = None

    def __init__(self, url: Url):
        """
        Instantiates any entity of a light novel hoster that can be identified with a url

        Inheriting classes should set a valid value for the _hoster and _hoster_abbreviation variables.

        :param url: the identifying url
        """
        super().__init__()
        self._url = url

    @property
    def url(self) -> Url:
        """The url that identifies this entity"""
        return self._url

    def change_url(self, **kwargs) -> Url:
        """
        Returns a url which uses this object's identifying url as basis and changes it if needed.

        :param kwargs: Changes to path, query or fragment. If not specified, the old properties are reused.
        :returns: A new url with a possibly altered path
        """
        url = self.url
        kwargs.setdefault('path', url.path)
        kwargs.setdefault('query', url.query)
        kwargs.setdefault('fragment', url.fragment)
        return Url(url.scheme, url.auth, url.hostname, url.port, kwargs['path'], kwargs['query'], kwargs['fragment'])


class Titled:
    _title: str = UNKNOWN

    @property
    def title(self) -> str:
        """The title"""
        return self._title

    @property
    def quoted_title(self):
        if self._title == UNKNOWN:
            return self._title
        return f"'{self._title}'"

    def __str__(self):
        return self.quoted_title


class Page(LightNovelEntity, Titled):
    """An html document of a light novel page"""
    _document: BeautifulSoup
    _success: bool

    def __init__(self, url: Url, document: BeautifulSoup):
        super().__init__(url)
        self._document = document
        self._success = False

    @property
    def document(self) -> BeautifulSoup:
        """The document that was loaded from the page"""
        return self._document

    @document.setter
    def document(self, value: BeautifulSoup):
        self._document = value

    @document.deleter
    def document(self):
        del self._document

    @property
    def success(self) -> bool:
        """Indicates whether the document was parsed successfully"""
        return self._success

    def _ensure_vars_changed(self, variables: Dict[str, object]):
        for var, default in variables.items():
            if getattr(self, var, default) == default:
                self.log.warning(f"Variable {var} ({str(default)}) unchanged after parsing.")

    def parse(self) -> bool:
        """Parses the page's document

        :returns: True if the parsing was successful. False otherwise.
        """
        self._success = self._parse()
        self._ensure_vars_changed({
            '_document': None,
            '_title': UNKNOWN,
        })
        return self.success

    def _parse(self) -> bool:
        """Internal method that parses the page's document

        Inheriting classes should override this method.
        :returns: True if the parsing was successful. False otherwise.
        """
        raise NotImplementedError('Must be overwritten')

    def __str__(self):
        return f"{self.quoted_title} {super().__str__()}".strip()


class Novel(Page, ABC):
    _description: Tag = None
    _author: str = UNKNOWN
    _translators: List[str] = []
    _editors: List[str] = []
    _language: str = UNKNOWN
    _rights: str = UNKNOWN
    _tags: List[str] = []
    _books: List['Book'] = []
    _cover_url: Url = None
    _cover: Image.Image = None
    _release_date: datetime = None

    def __init__(self, url: Url, document: BeautifulSoup):
        super().__init__(url, document)
        self._author = UNKNOWN
        self._translators = []
        self._editors = []
        self._language = UNKNOWN
        self._rights = UNKNOWN
        self._tags = []
        self._books = []

    @property
    def description(self) -> Optional[Tag]:
        """The description of this novel"""
        return self._description

    @property
    def author(self) -> str:
        """The author of this novel"""
        return self._author

    @property
    def translators(self) -> List[str]:
        """The translators of this novel"""
        return self._translators

    @property
    def editors(self) -> List[str]:
        """The editors of this novel"""
        return self._editors

    @property
    def language(self) -> str:
        """The language of this novel"""
        return self._language

    @property
    def copyright(self) -> Optional[str]:
        """The copyright of this novel"""
        return self._rights

    @property
    def tags(self) -> List[str]:
        """The tags that were assigned to this novel"""
        return self._tags

    @property
    def books(self) -> List['Book']:
        """The books of this novel"""
        return self._books

    @property
    def cover_url(self) -> Optional[Url]:
        """The url to the cover art of this novel"""
        return self._cover_url

    @property
    def cover(self) -> Optional[Image.Image]:
        """The cover art or this novel"""
        return self._cover

    @cover.setter
    def cover(self, value: Image.Image):
        self._cover = value

    @property
    def release_date(self) -> Optional[datetime]:
        """The date of the release of the novel"""
        return self._release_date

    def parse(self) -> bool:
        """Parses this novel's document

        :returns: True if the parsing was successful. False otherwise.
        """
        result = super().parse()
        self._ensure_vars_changed({
            '_description': None,
            '_author': UNKNOWN,
            '_language': UNKNOWN,
            '_rights': None,
            '_books': [],
            '_cover_url': None,
            '_release_date': None,
        })
        return result

    def generate_chapter_entries(self) -> Generator[Tuple['Book', 'ChapterEntry'], None, None]:
        """Generates all the parsed books and their chapter entries and assigns them their index.

        :returns: A generator that produces Book-ChapterEntry pairs.
        """
        book_n = 0
        chapter_n_abs = 0
        for book in self.books:
            book_n += 1
            book.number = book_n
            for chapter_entry in book.generate_chapter_entries():
                chapter_n_abs += 1
                chapter_entry.abs_index = chapter_n_abs
                yield book, chapter_entry

    def __str__(self):
        return f"{super().__str__()} by {self.author}"


class Indexed:
    _index: int = 0

    @property
    def index(self) -> int:
        """The index of this entity"""
        return self._index

    @index.setter
    def index(self, value: int):
        self._index = value

    def __str__(self):
        return str(self._index)


class AbsoluteIndexed(Indexed):
    _abs_index: int = 0

    @property
    def abs_index(self) -> int:
        """The absolute index of this entity"""
        return self._abs_index

    @abs_index.setter
    def abs_index(self, value: int):
        self._abs_index = value

    def __str__(self):
        return f"({self.abs_index}) {super().__str__()}"


class Book(Indexed, Titled):
    _chapter_entries: List['ChapterEntry'] = []
    _novel: 'Novel' = None

    def __init__(self, title: str):
        super().__init__()
        self._title = title
        self._chapter_entries = []

    @property
    def chapter_entries(self) -> List['ChapterEntry']:
        """All the chapter entries in this book"""
        return self._chapter_entries

    @property
    def novel(self) -> 'Novel':
        """The novel this book belongs to"""
        return self._novel

    @novel.setter
    def novel(self, value: 'Novel'):
        self._novel = value

    def generate_chapter_entries(self) -> Generator['ChapterEntry', None, None]:
        """Generates all chapter entries in the book and assigns them their index

        :returns: A generator of chapter entries
        """
        index = 0
        for chapter_entry in self._chapter_entries:
            index += 1
            chapter_entry.index = index
            yield chapter_entry

    def __str__(self):
        return f"{self._index} {self.quoted_title} ({len(self._chapter_entries)} entries)"


class ChapterEntity(AbsoluteIndexed, LightNovelEntity):
    _mime_type: MimeTypeTag = MimeTypeTag('text', 'html')

    @property
    def mime_type(self) -> MimeTypeTag:
        """The mime type of the chapter entity. Used for cache related actions."""
        return self._mime_type

    @property
    def accept_header(self) -> dict:
        return {'Accept': self._mime_type}

    def _create_chapter_entry(self, url: Url, offset: int) -> Optional['ChapterEntry']:
        """Creates a chapter entry from a path and an offset

        :param url: The url of the chapter entry to be.
        :param offset: The offset to be applied on the index (usually 1 or -1).
        :return: A new instance of a ChapterEntry if the path is not None.
        """
        if url is None:
            return None
        chapter_entry = ChapterEntry(url)
        chapter_entry.index = self.index + offset
        chapter_entry.abs_index = self.abs_index + offset
        return chapter_entry


class ChapterEntry(ChapterEntity, Titled):

    def __init__(self, url: Url, title: str = UNKNOWN):
        super().__init__(url)
        self._title = title

    @property
    def spoof_url(self) -> Url:
        """The url to use by the cache to store the resulting chapter"""
        return self._url

    def __str__(self):
        return f"{super().__str__()} {self.quoted_title} ({self.url})"


class Chapter(Page, ChapterEntity, ABC):
    _previous_chapter: Optional[Url] = None
    _next_chapter: Optional[Url] = None
    _content: Tag = None
    _book: Book = None
    _stop_if_not_complete: bool = True

    @property
    def content(self) -> Optional[Tag]:
        """The content of this chapter"""
        return self._content

    @property
    def stop_if_not_complete(self) -> bool:
        """Whether the chapter generation should stop if a chapter is not complete"""
        return self._stop_if_not_complete

    @property
    def previous_chapter(self) -> Optional[ChapterEntry]:
        """The chapter entry for the previous chapter if the link exists"""
        return self._create_chapter_entry(self._previous_chapter, -1)

    @property
    def next_chapter(self) -> Optional[ChapterEntry]:
        """The chapter entry for the next chapter if the link exists"""
        return self._create_chapter_entry(self._next_chapter, 1)

    @property
    def book(self) -> Optional[Book]:
        """The book this chapter belongs to"""
        return self._book

    def parse(self) -> bool:
        """Parses this chapter's document

        :returns: True if the parsing was successful. False otherwise.
        """
        result = super().parse()
        self._ensure_vars_changed({
            '_content': None,
        })
        return result

    def extract_clean_title(self) -> str:
        """Try to get the title as clean as possible"""
        title = self.quoted_title.strip("' ")
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
        """Cut the matching part or a string"""
        return string[:match.span(0)[0]] + string[match.span(0)[1]:]

    def is_complete(self) -> bool:
        """Whether the chapter has been completely published or not (partial/restricted access)"""
        raise NotImplementedError('Must be overwritten')

    def clean_content(self):
        """Clean the content of the chapter"""
        raise NotImplementedError('Must be overwritten')

    def __del__(self):
        if self._book is not None:
            del self._book
        if self._content is not None:
            del self._content
        if self._document is not None:
            del self._document

    def __str__(self):
        if self._book is None:
            return f"({self._abs_index}) ?.{self._index} {self.extract_clean_title()}"
        return f"({self._abs_index}) {self._book.index}.{self._index} {self.extract_clean_title()}"


class NovelEntry(Titled, LightNovelEntity):
    def __init__(self, url: Url, title: str):
        super().__init__(url)
        self._title = title


class ChapterFetchStrategy:
    log: logging.Logger = None
    _api: 'LightNovelApi' = None
    _adapter: BaseAdapter = None
    _blacklist: Set[str] = set()

    def __init__(self, api: 'LightNovelApi'):
        self.log = logging.getLogger(self.__class__.__name__)
        self._api = api
        self._adapter = api.adapter
        self._blacklist = set()

    def generate_chapters(self, novel: Novel) -> Generator[Tuple[Book, Chapter], None, None]:
        """
        Generates all the chapters of a novel, including those not listed on the chapter index.

        :param novel: The novel of which the chapters shall be generated.
        :return: A generator for book-chapter pairs
        """
        book = None
        chapter = None
        self._reset_blacklist()
        try:
            for book, chapter in self._fetch_indexed_chapters(novel):
                yield book, chapter
            for chapter in self._fetch_linked_chapters(chapter):
                yield book, chapter
        except LoopingListError as lle:
            self.log.warning(lle)
        except ParseError as pe:
            self.log.error(pe)
            adapter = self._adapter
            if isinstance(adapter, FileCacheAdapter):
                if not adapter.restore_backup():
                    adapter.delete(pe.chapter.url, pe.chapter.accept_header)

    def _reset_blacklist(self):
        """
        Resets the url blacklist for already processed urls.
        """
        self._blacklist = set()

    def _check_blacklist(self, chapter_entry: ChapterEntry):
        """
        Checks whether the given chapter entry has already been processed.

        :param chapter_entry: The chapter entry to check.
        :raise LoopingListError: The chapter entry has been processed before.
        """
        if chapter_entry.url.url in self._blacklist:
            raise LoopingListError(chapter_entry)

    def _add_to_blacklist(self, chapter_entry: ChapterEntry):
        """
        Adds a chapter entry to the blacklist so it doesn't get processed again in case of circular links.

        :param chapter_entry: The chapter entry to blacklist.
        """
        self._blacklist.add(chapter_entry.url.url)

    def _should_download_chapter(self, chapter_entry: ChapterEntry) -> bool:
        """
        Decides whether to download the chapter.

        Only applies to chapters from the chapter index.
        :param chapter_entry: The chapter entry to check for download eligibility
        :return: True if the chapter should be downloaded. False otherwise.
        """
        raise NotImplementedError('Must be overwritten')

    def _fetch_indexed_chapters(self, novel: Novel) -> Generator[Tuple[Book, Chapter], None, None]:
        """
        Generates all chapters from the chapter index.
        
        If there's no chapters generated at the end, the last chapter will be generated to allow for following
        chapter links.
        :param novel: The novel whose chapter index should be processed.
        :return: A generator of book-chapter pairs.
        """
        book = None
        chapter_entry = None
        chapter = None
        for book, chapter_entry in novel.generate_chapter_entries():
            self._check_blacklist(chapter_entry)
            if self._should_download_chapter(chapter_entry):
                chapter = self._fetch_chapter(chapter_entry)
                yield book, chapter
            self._add_to_blacklist(chapter_entry)
        if chapter_entry is None:
            self.log.warning("No chapters were generated from the chapter index.")
            return
        if chapter is None:
            self.log.info(f"Getting chapter {chapter_entry} to follow next chapters.")
            chapter = self._fetch_chapter(chapter_entry)
            yield book, chapter

    def _fetch_linked_chapters(self, last_chapter: Chapter) -> Generator[Chapter, None, None]:
        """
        Generates chapters based on the last indexed chapter by following their next chapter link.

        :param last_chapter: The last chapter that was in the chapter index.
        :return: A generator for chapters.
        """
        if not last_chapter.parse() or last_chapter.next_chapter is None:
            return
        self.log.info("Chapter index on novel page exhausted, but a link to the next chapter is present.")
        adapter = self._adapter
        chapter = last_chapter
        while chapter.success and chapter.next_chapter is not None:
            chapter_entry = chapter.next_chapter
            self._check_blacklist(chapter_entry)
            last_chapter = chapter
            chapter = self._fetch_next_chapter(last_chapter)
            self._add_to_blacklist(chapter_entry)
            if chapter.next_chapter is None and isinstance(adapter, FileCacheAdapter) and adapter.hit:
                chapter = self._check_whether_remote_has_next_chapter_link(chapter)
            yield chapter
            self._add_to_blacklist(chapter_entry)

    def _fetch_next_chapter(self, last_chapter: Chapter) -> Chapter:
        next_chapter = last_chapter.next_chapter
        self.log.debug(f"Following existing link to the next chapter {next_chapter}.")
        return self._fetch_chapter(next_chapter)

    def _fetch_chapter(self, chapter_entry: ChapterEntry) -> Chapter:
        """
        Gets the next chapter from the last parsed chapter.

        :param chapter_entry: The chapter entry to be fetched.
        :returns: A Chapter instance to be parsed.
        """
        self._check_blacklist(chapter_entry)
        return self._api.get_chapter_by_entry(chapter_entry)

    def _check_whether_remote_has_next_chapter_link(self, chapter: Chapter) -> Chapter:
        """
        Checks whether the remote chapter has an updated link to the next chapter and returns the new chapter.

        :param chapter: The chapter to check for an update.
        :return: An updated version of the chapter if available.
        """
        adapter = self._adapter
        if isinstance(adapter, FileCacheAdapter):
            adapter.backup_and_miss_next_request = True
            chapter = self._api.get_chapter(chapter.url)
            if not chapter.parse():
                raise ParseError(chapter)
            if chapter.next_chapter is None:
                self.log.info(f"Could not find updated link to the next chapter from the remote chapter {chapter}")
                adapter.restore_backup()
        else:
            self.log.warning("Cannot check for an updated remote because I'm not using the file cache.")
        return chapter


# noinspection DuplicatedCode
class AllChapterFetchStrategy(ChapterFetchStrategy):
    def _should_download_chapter(self, chapter_entry: ChapterEntry) -> bool:
        return True


class UpdatedChapterFetchStrategy(ChapterFetchStrategy):
    def _should_download_chapter(self, chapter_entry: ChapterEntry) -> bool:
        cached = self._chapter_already_downloaded(chapter_entry)
        if cached:
            self.log.info(f"Chapter {chapter_entry} already downloaded.")
        else:
            self.log.info(f"Chapter {chapter_entry} is new.")
        return not cached

    def _chapter_already_downloaded(self, chapter_entry: ChapterEntry) -> bool:
        adapter = self._adapter
        return isinstance(adapter, FileCacheAdapter) and adapter.would_hit(chapter_entry.spoof_url,
                                                                           {'Accept': str(chapter_entry.mime_type)})


class LightNovelApi(Hosted, ABC):
    _session: Session

    def __init__(self, session: Session = Session()):
        """Creates a new API for a specific service.

        :param session: The session to use when executing HTTP requests.
        """
        self.log = logging.getLogger(self.__class__.__name__)
        self._session = session
        if type(session.get_adapter('https://')) not in [FileCacheAdapter, HarAdapter]:
            self.log.warning("Not using a caching adapter will take a long time for every run.")

    @property
    def novel_url(self) -> str:
        """
        The url to the novels. Used for listing cached novels.
        """
        raise NotImplementedError('Must be overwritten')

    @property
    def session(self) -> Session:
        """The session the API uses to make HTTP requests"""
        return self._session

    @session.setter
    def session(self, value: Session):
        self._session = value

    @property
    def adapter(self) -> BaseAdapter:
        """The adapter of the session in use"""
        if isinstance(self._session, Browser):
            return self._session.adapter
        return self._session.get_adapter('https://')

    @property
    def fetch_all(self) -> ChapterFetchStrategy:
        return AllChapterFetchStrategy(self)

    @property
    def fetch_updated(self) -> ChapterFetchStrategy:
        return UpdatedChapterFetchStrategy(self)

    def _request_preparation(self, kwargs: dict) -> Tuple[dict, dict]:
        """Prepares kwargs before a request is made by splitting off additional arguments

        :param kwargs: The arguments to process.
        :returns: kwargs for the requests library and for the json library.
        """
        spoof_url_key = 'spoof_url'
        json_kwargs = kwargs.get('json', {})
        if 'json' in kwargs:
            del kwargs['json']
        if spoof_url_key in kwargs:
            spoof_url = kwargs[spoof_url_key]
            adapter = self.adapter
            if isinstance(adapter, FileCacheAdapter):
                adapter.next_request_cache_url = spoof_url
            else:
                self.log.warning(
                    f"Could not set spoof url ({spoof_url}) for cache as adapter is not a FileCacheAdapter.")
            del kwargs[spoof_url_key]
        return kwargs, json_kwargs

    def _get_html_document(self, url: Url, **kwargs: Any) -> BeautifulSoup:
        """Downloads an html document from a given url.

        :param url: The url where the document is located at.
        :param kwargs: Additional args to convey to the requests library.
        :return: An instance of BeautifulSoup which represents the html document.
        """
        kwargs.setdefault('headers', {}).setdefault('Accept', 'text/html')
        requests_kwargs, json_kwargs = self._request_preparation(kwargs)
        if len(json_kwargs) > 0:
            self.log.warning("Unnecessary json kwargs passed. Ignoring.")
        if isinstance(self._session, Browser):
            if isinstance(self._session.adapter, FileCacheAdapter):
                self._session.adapter.backup_and_miss_next_request = False
            response = self._session.navigate(url.url, **requests_kwargs)
        else:
            response = self._session.get(url.url, **requests_kwargs)
        return BeautifulSoup(response.text, features="html5lib")

    def _get_json_document(self, url: Url, **kwargs: Any) -> dict:
        """Downloads a json document from a given url.

        :param url: The url where the document is located at.
        :param kwargs: Additional args to convey to the requests library or to the json library (dict under 'json').
        :return: An instance of BeautifulSoup which represents the html document.
        """
        kwargs.setdefault('headers', {}).setdefault('Accept', 'application/json')
        requests_kwargs, json_kwargs = self._request_preparation(kwargs)
        if isinstance(self._session, Browser):
            response = self._session.navigate(url.url, **requests_kwargs)
        else:
            response = self._session.get(url.url, **requests_kwargs)
        response.encoding = 'utf8'
        return response.json(**json_kwargs)

    def get_image(self, url: Url, **kwargs: Any) -> Image.Image:
        """Downloads an image from a url.

        :param url: The url of the image.
        :param kwargs: Additional args to convey to the requests library.
        :return: An image object representation.
        """
        requests_kwargs, json_kwargs = self._request_preparation(kwargs)
        if len(json_kwargs) > 0:
            self.log.warning("Unnecessary json kwargs passed. Ignoring.")
        response = self._session.get(url.url, **requests_kwargs)
        return Image.open(BytesIO(response.content))

    def _get_novel(self, url: Url, **kwargs: Any) -> Novel:
        """Downloads the main page of the novel from the given url.

        Inheriting classes may override this method to adjust the novel class.
        :param url: The url where the page is located at.
        :param kwargs: Additional args to convey to the requests library.
        :return: An instance of a Novel.
        """
        return Novel(url, self._get_html_document(url, **kwargs))

    def get_novel(self, url: Url) -> Optional[Novel]:
        """Downloads the main page of the novel from the given url and parses it.

        This method downloads the latest version from the web and if it does not parse, restores from the backup.
        :param url: The url where the page is located at.
        :return: An instance of a Novel.
        """
        adapter = self.adapter
        if isinstance(adapter, FileCacheAdapter):
            adapter.backup_and_miss_next_request = True
        novel = self._get_novel(url)
        if not novel.parse():
            self.log.error("Couldn't parse novel page.")
            if isinstance(adapter, FileCacheAdapter):
                adapter.restore_backup()
            return None
        novel.cover = self.get_image(novel.cover_url)
        return novel

    def get_chapter(self, url: Url, **kwargs: Any) -> Chapter:
        """Downloads a chapter from the given url.

        Inheriting classes may override this method to adjust the chapter class.
        :param url: The url where the chapter is located at.
        :param kwargs: Additional args to convey to the requests library.
        :return: An instance of a Chapter.
        """
        return Chapter(url, self._get_html_document(url, **kwargs))

    def get_chapter_by_entry(self, chapter_entry: ChapterEntry, already_processed=None, **kwargs: Any) -> Chapter:
        """Downloads a chapter from the given chapter entry.

        :param chapter_entry: The ChapterEntry for the chapter.
        :param already_processed: A list to append the fetched url to.
        :param kwargs: Additional args to convey to the requests library.
        :return: An instance of a Chapter.
        """
        if already_processed is None:
            already_processed = []
        if chapter_entry.spoof_url != chapter_entry.url:
            kwargs.setdefault('spoof_url', chapter_entry.spoof_url)
        chapter = self.get_chapter(chapter_entry.url, **kwargs)
        chapter.index = chapter_entry.index
        chapter.abs_index = chapter_entry.abs_index
        already_processed.append(chapter_entry.url.url)
        return chapter

    def search(self, **kwargs) -> List[NovelEntry]:
        """Searches for a novel by title.

        :param kwargs: The search parameters to use.
        :return: A list of SearchEntry.
        """
        raise NotImplementedError('Must be overwritten')

    def matches(self, url: Url) -> bool:
        """
        Test if a url is being covered by this hoster

        :param url: The url to test.
        :return: True if this hoster indeed serves this url.
        """
        return are_schemelessly_same_site(url, self._hoster_homepage)

    @staticmethod
    def get_api(url: Url, apis: List['LightNovelApi'] = None) -> 'LightNovelApi':
        """Probes all available api wrappers and returns the first one that matches with the url.

        :param url: The url to be checked for.
        :param apis: The apis to check for matches for. Defaults to all applicable apis.
        :return: An instance of a LightNovelApi.
        """
        if apis is None:
            from lightnovel.wuxiaworld_com import WuxiaWorldComApi
            from lightnovel.webnovel_com import WebNovelComApi
            apis = [
                WuxiaWorldComApi(),
                WebNovelComApi(),
            ]
        for api in apis:
            if api.matches(url):
                return api
        raise LookupError(f"No api found for url {url}.")
