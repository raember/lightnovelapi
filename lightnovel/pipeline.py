import logging
import os
import re
from abc import ABC
from typing import Generator
from typing import Tuple

from api import Book, Chapter, Novel
from epub import EpubFile, BookFile, ChapterFile
from util import slugify, make_sure_dir_exists
# noinspection PyProtectedMember
from webot import Browser
from webot.adapter import CacheAdapter


class Pipeline(ABC):
    log: logging.Logger

    def __init__(self):
        self.log = logging.getLogger(self.__class__.__name__)

    def wrap(self, gen: Generator[Tuple[Book, Chapter], None, None]) -> Generator[Tuple[Book, Chapter], None, None]:
        raise NotImplementedError


class Parser(Pipeline):
    def __init__(self, browser: Browser):
        super().__init__()
        self._adapter = browser.session.get_adapter('https://')

    def wrap(self, gen: Generator[Tuple[Book, Chapter], None, None]) -> Generator[Tuple[Book, Chapter], None, None]:
        for book, chapter in gen:
            chapter._book = book
            if not chapter.parse():
                self.log.warning(f"Failed parsing chapter {chapter}")
                return
            else:
                if chapter.is_complete():
                    self.log.info(f"Got chapter {chapter} ({chapter.url})")
                    del chapter.document
                    book.chapters.append(chapter)
                    yield book, chapter
                else:
                    self.log.warning("Chapter not complete.")
                    if isinstance(self._adapter, CacheAdapter):
                        self._adapter.delete_last()
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
        first._next_chapter_path = second.next_chapter.path
        first.content.append(second.content)
        # Delete the second chapter from the list of chapters from the book
        DeleteChapters.delete_chapter(second)


class Output(Pipeline, ABC):

    def __init__(self, novel: Novel, ext: str, out_path: str = 'out'):
        super(Output, self).__init__()
        if not novel.success:
            self.log.warning("Novel wasn't parsed successfully.")
        self.novel = novel
        self.ext = ext
        self.out_path = out_path
        self.slug_title = slugify(novel.title, lowercase=False)
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

    def wrap(self, gen: Generator[Tuple[Book, Chapter], None, None]) -> Generator[Tuple[Book, Chapter], None, None]:
        unique_id = slugify(self.novel.title)
        filepath = self.join_to_path(self.filename)
        with EpubFile(
                file=filepath,
                unique_id=unique_id,
                title=self.novel.title,
                language=self.novel.language if self.novel.language else '',
                identifier=str(self.novel.url),
                rights=self.novel.rights if self.novel.rights else '',
                publisher=self.novel.url.hostname,
                subject=' / '.join(['Web Novel', *(self.novel.tags if self.novel.tags else [])]),
                date=self.novel.release_date,
                description=self.novel.description.text,
                creator=self.novel.author if self.novel.author else self.novel.translator if self.novel.translator else '',
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

    @staticmethod
    def delete_chapter(chapter: Chapter):
        chapter.book.chapters.remove(chapter)
        del chapter
