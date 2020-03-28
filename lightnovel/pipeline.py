import logging
import os
import re
from abc import ABC
from datetime import datetime, timedelta
from sys import getsizeof
from typing import Generator, Dict
from typing import Tuple

from hurry.filesize import size, alternative
# noinspection PyProtectedMember
from requests import Session
from spoofbot import Browser
from spoofbot.adapter import FileCacheAdapter

from api import Book, Chapter, Novel
from epub import EpubFile, BookFile, ChapterFile
from util import slugify, make_sure_dir_exists


class Pipeline(ABC):
    log: logging.Logger

    def __init__(self):
        self.log = logging.getLogger(self.__class__.__name__)

    def wrap(self, gen: Generator[Tuple[Book, Chapter], None, None]) -> Generator[Tuple[Book, Chapter], None, None]:
        raise NotImplementedError


class Parser(Pipeline):
    def __init__(self, session: Session):
        super().__init__()
        self._adapter = session.get_adapter('https://')

    def wrap(self, gen: Generator[Tuple[Book, Chapter], None, None]) -> Generator[Tuple[Book, Chapter], None, None]:
        for book, chapter in gen:
            chapter._book = book
            if not chapter.success and not chapter.parse():
                self.log.warning(f"Failed parsing chapter {chapter}")
                if isinstance(self._adapter, FileCacheAdapter):
                    self._adapter.delete_last()
                return
            else:
                if chapter.is_complete():
                    self.log.info(f"Got chapter {chapter} ({chapter.url})")
                    yield book, chapter
                else:
                    self.log.warning("Chapter not complete.")
                    if isinstance(self._adapter, FileCacheAdapter):
                        self._adapter.delete_last()
                    if chapter.stop_if_not_complete:
                        return


class HtmlCleaner(Pipeline):
    def wrap(self, gen: Generator[Tuple[Book, Chapter], None, None]) -> Generator[Tuple[Book, Chapter], None, None]:
        for book, chapter in gen:
            chapter.clean_content()
            self.log.debug(f"Cleaned content of {chapter}")
            yield book, chapter


class ChapterConflation(Pipeline):
    def __init__(self, novel: Novel):
        super().__init__()
        self.novel = novel

    def wrap(self, gen: Generator[Tuple[Book, Chapter], None, None]) -> Generator[Tuple[Book, Chapter], None, None]:
        last_book = None
        last_chap = None
        for book, chapter in gen:
            if book != last_book:  # New book. First chapter. Can't conflate chapters across books.
                if last_book is not None:  # First chapter of at least second book. Yield cached one and cache new one.
                    yield last_book, last_chap
                last_book = book
                last_chap = chapter
                last_chap._index = 1
                continue

            if self.can_be_conflated(last_chap, chapter):
                self.log.debug(f"Conflating chapter '{last_chap.title}' with '{chapter.title}'")
                self.conflate(last_chap, chapter)
            else:  # Different chapter. Yield cached one and cache new one.
                self.log.debug(f"Cannot conflate the old chapter ({last_chap}) with chapter {chapter}")
                yield book, last_chap
                last_chap = chapter
                last_chap.index += 1
        self.log.debug("Source generator finished. Yielding last chapter")
        yield last_book, last_chap

    @staticmethod
    def can_be_conflated(first: Chapter, second: Chapter) -> bool:
        pattern = re.compile(r'[\w\d]+')
        owns = pattern.findall(first.extract_clean_title())
        others = pattern.findall(second.extract_clean_title())
        for own, other in zip(owns, others):
            if own != other:
                return False
        return True

    @staticmethod
    def conflate(first: Chapter, second: Chapter):
        first._next_chapter = second.next_chapter.url.path
        first.content.append(second.content)
        # Delete the second chapter from the list of chapters from the book
        DeleteChapters.delete_chapter(second)


class Output(Pipeline, ABC):

    def __init__(self, novel: Novel, ext: str, out_path: str = 'out'):
        super().__init__()
        if not novel.success:
            self.log.warning("Novel wasn't parsed successfully.")
        self.novel = novel
        self.ext = ext
        self.out_path = out_path
        self.slug_title = slugify(novel.title)
        self.filename = f"{self.slug_title}.{self.ext}"
        self.path = os.path.join(out_path, self.novel.url.hostname)
        make_sure_dir_exists(self.path)

    def join_to_path(self, *paths: str) -> str:
        return os.path.join(self.path, *paths)


class EpubMaker(Output):  # TODO: Add an Epub maker that splits by book
    ALLOWED_TAGS = [
        'a', 'abbr', 'acronym', 'applet', 'b', 'bdo', 'big', 'br', 'cite', 'code', 'del', 'dfn', 'em', 'i', 'iframe',
        'img', 'ins', 'kbd', 'map', 'noscript', 'ns:svg', 'object', 'q', 'samp', 'script', 'small', 'span', 'strong',
        'sub', 'sup', 'tt', 'var',
        # Added:
        'p', 'div', 'hr'
    ]

    def __init__(self, novel: Novel, out_path: str = 'out'):
        super().__init__(novel, 'epub', out_path)

    # TODO: Allow for incremental addition of new chapters
    def wrap(self, gen: Generator[Tuple[Book, Chapter], None, None]) -> Generator[Tuple[Book, Chapter], None, None]:
        unique_id = slugify(self.novel.title)
        filepath = self.join_to_path(self.filename)
        with EpubFile(
                file=filepath,
                unique_id=unique_id,
                title=self.novel.title,
                language=self.novel.language if self.novel.language else '',
                identifier=str(self.novel.url),
                rights=self.novel.copyright if self.novel.copyright else '',
                publisher=self.novel.url.hostname,
                subject=' / '.join(['Web Novel', *(self.novel.tags if self.novel.tags else [])]),
                date=self.novel.release_date,
                description=self.novel.description.text,
                creator=self.novel.author if self.novel.author else self.novel.translators if self.novel.translators else '',
                cover_image=self.novel.cover,
                mode='w') as epub:
            self.log.debug(f"Opened file '{filepath}'")
            last_book = None
            for book, chapter in gen:
                if book != last_book:  # New book
                    last_book = book
                    book = chapter.book
                    book_file = BookFile(book)
                    epub.add_book(book_file)
                    self.log.debug(f"Saved book {book} to ({book_file.unique_id}): {book_file.filepath}")
                chapter_file = ChapterFile(chapter)
                epub.add_chapter(book_file, chapter_file)
                self.log.debug(f"Saved chapter {chapter} to ({chapter_file.unique_id}): {chapter_file.filepath}")
                yield book, chapter


class DeleteChapters(Pipeline):
    def wrap(self, gen: Generator[Tuple[Book, Chapter], None, None]) -> Generator[Tuple[Book, Chapter], None, None]:
        for book, chapter in gen:
            self.delete_chapter(chapter)
            self.log.debug(f"Deleted chapter {chapter}")
            yield book, chapter

    # noinspection PyUnusedLocal
    @staticmethod
    def delete_chapter(chapter: Chapter):
        del chapter


class Statistic:
    new: int = 0
    total: int = 0
    followed: int = 0
    document_size: int = 0
    content_size: int = 0
    started: datetime = datetime.now()
    ended: datetime = datetime.now()

    def __init__(self):
        self.started = datetime.now()
        self.ended = datetime.now()

    @property
    def old(self) -> int:
        return self.total - self.new

    @property
    def duration(self) -> timedelta:
        return self.ended - self.started


class StatisticsMaker(Pipeline):
    _browser: Browser
    _novels: Dict[Novel, Statistic]
    _overall: Statistic

    def __init__(self, browser: Browser):
        super().__init__()
        self._browser = browser
        self._novels = {}
        self._overall = Statistic()

    def wrap(self, gen: Generator[Tuple[Book, Chapter], None, None]) -> Generator[Tuple[Book, Chapter], None, None]:
        self._overall.started = datetime.now()
        urls = set()
        for book, chapter in gen:
            stat = self._novels.get(book.novel, Statistic())
            stat.ended = datetime.now()
            self._overall.ended = datetime.now()
            adapter = self._browser.adapter
            if isinstance(adapter, FileCacheAdapter):
                if not adapter.hit:
                    stat.new += 1
                    self._overall.new += 1
                else:
                    stat.followed += 1
                    self._overall.followed += 1
            if chapter.url.url not in urls:
                if chapter.content is not None:
                    content_size = getsizeof(str(chapter.content))
                else:
                    content_size = 0
                stat.content_size += content_size
                stat.document_size += getsizeof(str(chapter.document))
            self._novels[book.novel] = stat
            urls.add(chapter.url.url)
            yield book, chapter

    def report(self):
        self.log.info("Statistics:")
        self.log.info(f"  new/followed/total")
        for novel, stats in self._novels.items():
            title = f"'{novel.title}' {novel.hoster_abbreviation},"
            rest, seconds = divmod(stats.duration.total_seconds(), 60)
            _, minutes = divmod(rest, 60)
            total = stats.new
            for book in novel.books:
                total += len(book.chapter_entries)
            stats.total = total
            self.log.info(f"{stats.new:>5d}/{stats.followed:^5d}/{total:<5d} new chapters "
                          f"in {title:<50s} "
                          f"taking {int(minutes):02}:{int(seconds):02} "
                          f"(from {stats.started.strftime('%Y-%m-%d %H:%M:%S')} "
                          f"until {stats.ended.strftime('%Y-%m-%d %H:%M:%S')}), "
                          f"storing {size(stats.content_size, system=alternative)} content "
                          f"and {size(stats.document_size, system=alternative)} documents")
            self._overall.total += stats.total
            self._overall.content_size += stats.content_size
            self._overall.document_size += stats.document_size
            if self._overall.started > stats.started:
                self._overall.started = stats.started
            if self._overall.ended < stats.ended:
                self._overall.ended = stats.ended
        self.log.info("Overall:")
        rest, seconds = divmod(self._overall.duration.total_seconds(), 60)
        rest, minutes = divmod(rest, 60)
        _, hours = divmod(rest, 60)
        self.log.info(f"{self._overall.new:>5d}/{self._overall.followed:^5d}/{self._overall.total:<5d} new chapters, "
                      f"{' ':<51s}"
                      f"taking {int(hours):02}:{int(minutes):02}:{int(seconds):02} "
                      f"(from {self._overall.started.strftime('%Y-%m-%d %H:%M:%S')} "
                      f"until {self._overall.ended.strftime('%Y-%m-%d %H:%M:%S')}), "
                      f"storing {size(self._overall.content_size, system=alternative)} content "
                      f"and {size(self._overall.document_size, system=alternative)} documents")
