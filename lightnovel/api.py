import json
import logging
import re
from abc import ABC
from datetime import datetime
from io import BytesIO
from typing import List, Any, Tuple, Generator, Optional, Set

from PIL import Image
from bs4 import BeautifulSoup
from bs4.element import Tag
from requests import Session
from requests.adapters import BaseAdapter
from spoofbot import Browser, MimeTypeTag
from spoofbot.adapter import FileCacheAdapter, HarAdapter
from spoofbot.util import are_schemelessly_same_site
from urllib3.util import Url

from lightnovel.util.text import normalize_string


class LoopingListException(Exception):
    """
    Exception for when a chapter in a novel has already been processed before.

    If a chapter has been processed before but was about to be processed yet again, this means that the list of chapters
    contains at least one duplicate.
    """

    def __init__(self, chapter_entry: 'ChapterEntry'):
        """
        Raise exception if the chapter entry to process has been processed before already.

        :param chapter_entry: The chapter entry that was identified as a duplicate.
        """
        super().__init__(f"The chapter has already been processed before: '{chapter_entry}'")


class ParseException(Exception):
    """
    Exception for a failed parsing stage of a chapter.

    If the structure of a chapter's underlying data differs from what the parsing method was built for, it cannot
    proceed to parse the chapter.
    """

    chapter: 'Chapter'

    def __init__(self, chapter: 'Chapter'):
        """
        Raise exception if the chapter's underlying data could not be parsed.

        :param chapter: The chapter with the faulty data.
        """
        super().__init__(f"Failed to parse chapter {chapter}.")
        self.chapter = chapter


class Hosted(ABC):
    """
    An entity that is associated with a hoster.
    """

    _hoster_base_url: Url = None
    _hoster_name: str = None
    _hoster_short_name: str = None

    @property
    def hoster_base_url(self) -> Url:
        """
        The URL to the hoster's home page

        Inheriting classes should set this value internally.
        """
        if self._hoster_base_url is None:
            raise NotImplementedError("Hoster base URL must be set by inheriting class")
        return self._hoster_base_url

    @property
    def hoster_name(self) -> str:
        """
        The name of the hoster.

        Inheriting classes should set this value internally.
        """
        if self._hoster_name is None:
            raise NotImplementedError("Hoster name must be set by inheriting class")
        return self._hoster_name

    @property
    def hoster_short_name(self) -> str:
        """
        A short representation of the hoster's name

        Inheriting classes should set this value internally.
        """
        if self._hoster_short_name is None:
            raise NotImplementedError("Hoster short name must be set by inheriting class")
        return self._hoster_short_name

    def change_url(self, url: Url = None, **kwargs) -> Url:
        """
        Return a URL which uses this object's identifying URL as basis and changes it if needed.

        :param kwargs: Changes to path, query or fragment. If not specified, the old properties are reused.
        :param url: The url to use as base. Equals hoster base url if None.
        :returns: A new  with a possibly altered path
        """
        url = self.hoster_base_url if url is None else url
        kwargs.setdefault('path', url.path)
        kwargs.setdefault('query', url.query)
        kwargs.setdefault('fragment', url.fragment)
        return Url(url.scheme, url.auth, url.hostname, url.port, kwargs['path'], kwargs['query'], kwargs['fragment'])

    def __str__(self):
        return self.hoster_name

    def __repr__(self):
        return f"{self.hoster_name}({self.hoster_base_url})"


class Logged(ABC):
    """Entity that has the ability to write logs itself."""

    log: logging.Logger = None

    def __init__(self):
        self.log = logging.getLogger(self.__class__.__name__)


class LightNovelEntity(Hosted, Logged, ABC):
    """Entity that is identified by a URL."""

    _url: Url = None

    def __init__(self, url: Url):
        """
        Instantiate any entity of a light novel hoster that can be identified with a URL.

        Inheriting classes should set a valid value for the _hoster and _hoster_abbreviation variables.

        :param url: The identifying URL
        """
        super().__init__()
        self._url = url

    @property
    def url(self) -> Url:
        """The URL that identifies this entity"""
        return self._url

    def change_url(self, **kwargs) -> Url:
        return super(LightNovelEntity, self).change_url(url=self.url, **kwargs)

    def __repr__(self):
        return f"{self.hoster_name}({self.url})"


class Titled(ABC):
    """Entity that has a title."""

    _title: str = None
    _is_chapter: bool = True

    @property
    def title(self) -> str:
        """The title"""
        if not self._title:
            return ''
        title1 = normalize_string(self._title)
        # Sometimes the title starts with "chapter (42): "
        if self._is_chapter:
            title2 = re.sub(r'^((chapter|vol(ume)?|book)?\s*[(\[]?\s*\d+\s*[)\]\-:;.,]*\s+)+', '', title1,
                            flags=re.IGNORECASE).strip('– ')
            if len(title2) == 0:
                return title1
        else:
            title2 = title1
        # Sometimes the title contains the index or a part "B"
        title3 = re.sub(r'[(\[]?(\d+[A-Z]?)[)\]]?\s+\.?$', '', title2, flags=re.IGNORECASE).strip('– ')
        if len(title3) == 0:
            return title2
        return title3

    def __str__(self):
        return self.title

    def __repr__(self):
        return self.title


class Document(ABC):
    """Document that is the result of an HTTP request"""
    _content: Any = None

    def __init__(self, content: Any):
        """
        Create a Document with a specific content.

        :param content: The content that the Document represents.
        """
        self._content = content

    @property
    def content(self) -> Any:
        return self._content

    @classmethod
    def from_string(cls, string: str, **kwargs) -> 'Document':
        """
        Create a document on the basis of a string as the underlying data.

        :param string: The string to base the document on.
        :param kwargs: Possible additional arguments.
        :return: An instance of a Document.
        """
        raise NotImplementedError("Must be overwritten")

    def __del__(self):
        """Make sure to delete the content from memory if the document gets deleted."""
        del self._content

    def __str__(self):
        return self._content

    def __repr__(self):
        return self.__class__.__name__


class HtmlDocument(Document):
    """HTML document that is the result of an HTTP request"""
    _content: BeautifulSoup = None

    def __init__(self, content: BeautifulSoup):
        """
        Create an HtmlDocument with a specific content.

        :param content: The content that the HtmlDocument represents.
        """
        super(HtmlDocument, self).__init__(content)

    @property
    def content(self) -> BeautifulSoup:
        return self._content

    @classmethod
    def from_string(cls, string: str, features: str = "html5lib") -> 'HtmlDocument':
        """
        Create an HTML document on the basis of a string as the underlying data.

        :param string: The HTML string to base the document on.
        :param features: Argument to pass to the BeautifulSoup parser.
        :return: An instance of an HtmlDocument.
        """
        return HtmlDocument(BeautifulSoup(string, features=features))


class JsonDocument(Document):
    """JSON document that is the result of an HTTP request"""
    _content: dict = None

    def __init__(self, content: dict):
        """
        Create an JsonDocument with a specific content.

        :param content: The content that the JsonDocument represents.
        """
        super(JsonDocument, self).__init__(content)

    @property
    def content(self) -> dict:
        return self._content

    @classmethod
    def from_string(cls, string: str) -> 'JsonDocument':
        """
        Create an JSON document on the basis of a string as the underlying data.

        :param string: The JSON string to base the document on.
        :return: An instance of an HtmlDocument.
        """
        return JsonDocument(json.loads(string))


class Page(LightNovelEntity, Titled, ABC):
    """An html document of a light novel page"""

    _document: Document
    _success: bool

    def __init__(self, url: Url, document: Document):
        """
        Create a page based on its URL and its content.

        :param url: The URL the page stems from.
        :param document: The document that is represented by the page.
        """
        super().__init__(url)
        self._document = document
        self._success = False

    @property
    def document(self) -> Document:
        """The document that was loaded from the page"""
        return self._document

    @document.setter
    def document(self, value: Document):
        """The document that was loaded from the page"""
        self._document = value

    @document.deleter
    def document(self):
        """The document that was loaded from the page"""
        del self._document

    @property
    def success(self) -> bool:
        """Indicate whether the document was parsed successfully"""
        return self._success

    def parse(self) -> bool:
        """Parse the page's document.

        :returns: True if the parsing was successful. False otherwise.
        """
        self._success = self._parse()
        return self.success

    def _parse(self) -> bool:
        """Internal method that parses the page's document

        Inheriting classes must override this method.
        :returns: True if the parsing was successful. False otherwise.
        """
        raise NotImplementedError('Must be overwritten')

    def __str__(self):
        return f'{self.title} {super().__str__()}'.strip()

    def __repr__(self):
        return f'{self.__class__.__name__}("{self.title}", "{self.url}")'


class Novel(Page, ABC):
    _description: Tag = None
    _author: str = None
    _translators: List[str] = []
    _editors: List[str] = []
    _language: str = None
    _rights: str = None
    _tags: List[str] = []
    _books: List['Book'] = []
    _cover_url: Url = None
    _cover: Image.Image = None
    _release_date: datetime = None

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

    def generate_chapter_entries(self) -> Generator[Tuple['Book', 'ChapterEntry'], None, None]:
        """
        Generate all the parsed books and their chapter entries and assigns them their index.

        :returns: A generator that produces Book-ChapterEntry pairs.
        """
        chapter_n_abs = 0
        for book_n, book in enumerate(self.books):
            book.number = book_n + 1
            for chapter_n, chapter_entry in enumerate(book.generate_chapter_entries()):
                chapter_n_abs += 1
                chapter_entry.abs_index = chapter_n_abs
                chapter_entry.index = chapter_n + 1
                yield book, chapter_entry

    def __str__(self):
        return f"{super().__str__()} by {self.author}"

    def __repr__(self):
        return f'{self.__class__.__name__}("{self.title}", "{self.url}")'


class Book(Titled, ABC):
    """A book of a novel"""

    _chapter_entries: List['ChapterEntry'] = []
    _novel: 'Novel' = None
    _index: int = 0

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

    @property
    def index(self) -> int:
        """The index of this book"""
        return self._index

    @index.setter
    def index(self, value: int):
        self._index = value

    def generate_chapter_entries(self) -> Generator['ChapterEntry', None, None]:
        """
        Generate all chapter entries in the book and assigns them their index

        :returns: A generator of chapter entries
        """
        index = 0
        for chapter_entry in self._chapter_entries:
            index += 1
            chapter_entry.index = index
            yield chapter_entry

    def __str__(self):
        return f'{self.index}: {self.title}'

    def __repr__(self):
        return f'{self.__class__.__name__}({self.index}, "{self.title}", {repr(self.novel)}, [{repr(self.chapter_entries)}])'


class ChapterEntity(LightNovelEntity, ABC):
    """Describe objects that vaguely describe chapters"""

    _mime_type: MimeTypeTag = MimeTypeTag('text', 'html')
    _index: int = 0
    _abs_index: int = 0

    @property
    def mime_type(self) -> MimeTypeTag:
        """The mime type of the chapter entity. Used for cache related actions."""
        return self._mime_type

    @property
    def accept_header(self) -> dict:
        return {'Accept': self._mime_type}

    @property
    def index(self) -> int:
        """The index of this chapter entry"""
        return self._index

    @index.setter
    def index(self, value: int):
        self._index = value

    @property
    def abs_index(self) -> int:
        """The absolute index of this chapter entry"""
        return self._abs_index

    @abs_index.setter
    def abs_index(self, value: int):
        self._abs_index = value

    def _create_chapter_entry(self, url: Url, offset: int) -> Optional['ChapterEntry']:
        """
        Create a chapter entry from a path and an offset

        :param url: The url of the chapter entry to be.
        :param offset: The offset to be applied on the index (usually 1 or -1).
        :return: A new instance of a ChapterEntry if the path is not None.
        """
        if url is None:
            return None
        chapter_entry = self._create_chapter_entry_from_url(url)
        chapter_entry.index = self.index + offset
        chapter_entry.abs_index = self.abs_index + offset
        return chapter_entry

    def _create_chapter_entry_from_url(self, url: Url) -> 'ChapterEntry':
        """
        Create a chapter entry from a url only.

        Subclasses must override and instantiate their specific subclass.

        :param url: The url of the chapter entry to be.
        :return: A new instance of a ChapterEntry.
        """
        raise NotImplementedError("Must override method")

    def __str__(self):
        return str(self.abs_index)

    def __repr__(self):
        return f'{self.__class__.__name__}({self.abs_index}, "{self.url}")'


class ChapterEntry(ChapterEntity, Titled, ABC):
    """Entry of a chapter"""

    def __init__(self, url: Url, title: str = None):
        super().__init__(url)
        self._title = title

    @property
    def spoof_url(self) -> Url:
        """
        The URL to use by the cache to store the resulting chapter

        Can be overwritten by subclasses. Useful if the URL of a chapter has a query and or a fragment that determines
        the specific chapter, because those get stripped for the caching process. Also useful if the path of the URL
        uses variables (i.e. timestamps) that would prevent a future hit in cache.
        """
        return self._url

    def __str__(self):
        return f'{super().__str__()}: "{self.title}" ({self.url})'

    def __repr__(self):
        return f'{self.__class__.__name__}({self.abs_index}, "{self.url}")'


class Chapter(Page, ChapterEntity, ABC):
    """A chapter with the chapter's contents"""

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

    @book.setter
    def book(self, value: Book):
        self._book = value

    def is_complete(self) -> bool:
        """Whether the chapter has been completely published or not (partial/restricted access)"""
        raise NotImplementedError('Must be overwritten')

    def clean_content(self):
        """Clean the content of the chapter"""
        raise NotImplementedError('Must be overwritten')

    def __del__(self):
        if self._book:
            del self._book
        if self._content:
            del self._content
        if self._document:
            del self._document

    def __str__(self):
        return f'{self._abs_index}({self._book.index if self._book else "?"}.{self._index}): "{self.title}"'

    def __repr__(self):
        return f'{self.__class__.__name__}({self.abs_index}, "{self.title}", "{self.url}")'


class NovelEntry(Titled, LightNovelEntity, ABC):
    """An entry of a listed novel"""
    _is_chapter = False

    def __init__(self, url: Url, title: str):
        super().__init__(url)
        self._title = title

    def __str__(self):
        return self.title

    def __repr__(self):
        return f'{self.__class__.__name__}("{self.title}", "{self.url}")'


class ChapterFetchStrategy:
    """The strategy for fetching chapters"""

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
        Generate all the chapters of a novel, including those not listed on the chapter index.

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
        except LoopingListException as lle:
            self.log.warning(lle)
        except ParseException as pe:
            self.log.error(pe)
            adapter = self._adapter
            if isinstance(adapter, FileCacheAdapter):
                if not adapter.restore_backup():
                    adapter.delete(pe.chapter.url, pe.chapter.accept_header)

    def _reset_blacklist(self):
        """Reset the url blacklist for already processed urls."""
        self._blacklist = set()

    def _check_blacklist(self, chapter_entry: ChapterEntry):
        """
        Check whether the given chapter entry has already been processed.

        :param chapter_entry: The chapter entry to check.
        :raise LoopingListException: The chapter entry has been processed before.
        """
        if chapter_entry.url.url in self._blacklist:
            raise LoopingListException(chapter_entry)

    def _add_to_blacklist(self, chapter_entry: ChapterEntry):
        """
        Add a chapter entry to the blacklist so it doesn't get processed again in case of circular links.

        :param chapter_entry: The chapter entry to blacklist.
        """
        self._blacklist.add(chapter_entry.url.url)

    def _should_download_chapter(self, chapter_entry: ChapterEntry) -> bool:
        """
        Decide whether to download the chapter.

        Only applies to chapters from the chapter index.

        :param chapter_entry: The chapter entry to check for download eligibility
        :return: True if the chapter should be downloaded. False otherwise.
        """
        raise NotImplementedError('Must be overwritten')

    def _fetch_indexed_chapters(self, novel: Novel) -> Generator[Tuple[Book, Chapter], None, None]:
        """
        Generate all chapters from the chapter index.
        
        If there's no chapters generated at the end, the last chapter will be generated to allow for following
        chapter links.
        :param novel: The novel whose chapter index should be processed.
        :return: A generator of book-chapter pairs.
        """
        book = None
        chapter_entry = None
        chapter = None

        # Cycle through all chapters listed on the novel's index
        for book, chapter_entry in novel.generate_chapter_entries():
            self._check_blacklist(chapter_entry)
            if self._should_download_chapter(chapter_entry):
                chapter = self._fetch_chapter(chapter_entry)
                yield book, chapter
                if not chapter.is_complete():
                    # Maybe this chapter was cached and should be updated
                    chapter = self._fetch_chapter(chapter_entry)
                    yield book, chapter
                if not chapter.is_complete():
                    # Chapter is definitely not complete
                    break
            self._add_to_blacklist(chapter_entry)

        if chapter_entry is None:
            self.log.warning("No chapters were generated from the chapter index.")
            return
        if chapter is None:
            self.log.info(f"Getting chapter {chapter_entry} to follow next chapters.")
            # Remove chapter entry from blacklist in order to fetch the chapter and parse it
            self._blacklist.remove(chapter_entry.url.url)
            chapter = self._fetch_chapter(chapter_entry)
            yield book, chapter

    def _fetch_linked_chapters(self, last_chapter: Chapter) -> Generator[Chapter, None, None]:
        """
        Generate chapters based on the last indexed chapter by following their next chapter link.

        :param last_chapter: The last chapter that was in the chapter index.
        :return: A generator for chapters.
        """
        if not last_chapter.success or last_chapter.next_chapter is None:
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
                # TODO: Unset active flag of cache and resend the request
                chapter = self._check_for_next_chapter_link_in_remote(chapter)
            yield chapter
            if not chapter.is_complete():
                # Maybe this chapter was cached and should be updated
                chapter = self._check_for_next_chapter_link_in_remote(chapter)
                yield chapter
            if not chapter.is_complete():
                # Chapter is definitely not complete
                break
            self._add_to_blacklist(chapter_entry)

    def _fetch_next_chapter(self, last_chapter: Chapter) -> Chapter:
        next_chapter_entry = last_chapter.next_chapter
        self.log.debug(f"Following existing link to the next chapter {next_chapter_entry}.")
        next_chapter = self._fetch_chapter(next_chapter_entry)
        if not next_chapter.parse():
            raise ParseException(next_chapter)
        next_chapter.book = last_chapter.book
        next_chapter.abs_index = last_chapter.abs_index + 1
        next_chapter.index = last_chapter.index + 1
        return next_chapter

    def _fetch_chapter(self, chapter_entry: ChapterEntry) -> Chapter:
        """
        Get the next chapter from the last parsed chapter.

        :param chapter_entry: The chapter entry to be fetched.
        :returns: A Chapter instance to be parsed.
        """
        self._check_blacklist(chapter_entry)
        return self._api.get_chapter_by_entry(chapter_entry)

    def _check_for_next_chapter_link_in_remote(self, chapter: Chapter) -> Chapter:
        """
        Check whether the remote chapter has an updated link to the next chapter and returns the new chapter.

        :param chapter: The chapter to check for an update.
        :return: An updated version of the chapter if available.
        """
        adapter = self._adapter
        if isinstance(adapter, FileCacheAdapter):
            adapter.backup_and_miss_next_request = True
            abs_index, index, book = chapter.abs_index, chapter.index, chapter.book
            chapter = self._api.get_chapter(chapter.url)
            chapter.abs_index, chapter.index, chapter.book = abs_index, index, book
            if not chapter.parse():
                raise ParseException(chapter)
            if chapter.next_chapter is None:
                self.log.info(f"Could not find updated link to the next chapter from the remote chapter {chapter}")
                adapter.restore_backup()
        else:
            self.log.warning("Cannot check for an updated remote because I'm not using the file cache.")
        return chapter

    def __repr__(self):
        return f'{self.__class__.__name__}({repr(self._api)})'


# noinspection DuplicatedCode
class AllChapterFetchStrategy(ChapterFetchStrategy):
    """The strategy for fetching all chapters of a novel"""

    def _should_download_chapter(self, chapter_entry: ChapterEntry) -> bool:
        """
        Indicate to download the chapter regardless

        :param chapter_entry: The chapter entry to check.
        :return: True if the chapter should be downloaded. False otherwise.
        """
        return True


class UpdatedChapterFetchStrategy(ChapterFetchStrategy):
    """The strategy for fetching only updated chapters of a novel"""

    def _should_download_chapter(self, chapter_entry: ChapterEntry) -> bool:
        """
        Check whether the chapter has not been downloaded before.

        :param chapter_entry: The chapter entry to check.
        :return: True if the chapter should be downloaded. False otherwise.
        """
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
    """An abstract api for a light novel hoster"""

    _session: Session

    def __init__(self, session: Session = Session()):
        """
        Create a new API for a specific service.

        :param session: The session to use when executing HTTP requests.
        """
        self.log = logging.getLogger(self.__class__.__name__)
        self._session = session
        if type(session.get_adapter('https://')) not in [FileCacheAdapter, HarAdapter]:
            self.log.warning("Not using a caching adapter will take a long time for every run.")

    @property
    def novel_url(self) -> str:
        """The url to the novels. Used for listing cached novels."""
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
        """
        Prepare kwargs before a request is made by splitting off additional arguments

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

    def _get_html_document(self, url: Url, **kwargs: Any) -> HtmlDocument:
        """
        Download an HTML document from a given url.

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
        return HtmlDocument.from_string(response.text)

    def _get_json_document(self, url: Url, **kwargs: Any) -> JsonDocument:
        """
        Download a JSON document from a given url.

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
        return JsonDocument(response.json(**json_kwargs))

    def get_image(self, url: Url, **kwargs: Any) -> Image.Image:
        """
        Download an image from a url.

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
        """
        Download the main page of the novel from the given url.

        Inheriting classes may override this method to adjust the novel class.
        :param url: The url where the page is located at.
        :param kwargs: Additional args to convey to the requests library.
        :return: An instance of a Novel.
        """
        return Novel(url, self._get_html_document(url, **kwargs))

    def get_novel(self, url: Url) -> Optional[Novel]:
        """
        Download the main page of the novel from the given url and parses it.

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
        """
        Download a chapter from the given url.

        Inheriting classes may override this method to adjust the chapter class.
        :param url: The url where the chapter is located at.
        :param kwargs: Additional args to convey to the requests library.
        :return: An instance of a Chapter.
        """
        return Chapter(url, self._get_html_document(url, **kwargs))

    def get_chapter_by_entry(self, chapter_entry: ChapterEntry, already_processed=None, **kwargs: Any) -> Chapter:
        """
        Download a chapter from the given chapter entry.

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

    def search(self, *args, **kwargs) -> List[NovelEntry]:
        """
        Search for a novel by title.

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
        return are_schemelessly_same_site(url, self._hoster_base_url)

    @staticmethod
    def get_api(url: Url, apis: List['LightNovelApi'] = None) -> 'LightNovelApi':
        """
        Probe all available api wrappers and returns the first one that matches with the url.

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
