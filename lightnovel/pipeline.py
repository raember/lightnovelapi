import logging
import re
from abc import ABC
from typing import Generator

from lightnovel import Chapter, Novel


class Pipeline(ABC):
    log: logging.Logger

    def __init__(self):
        self.log = logging.getLogger(self.__class__.__name__)

    def wrap(self, gen: Generator[Chapter, None, None]) -> Generator[Chapter, None, None]:
        for chapter in gen:
            yield self._consume(chapter)

    def _consume(self, chapter: Chapter) -> Chapter:
        raise NotImplementedError


class ChapterConflation(Pipeline):
    def __init__(self, novel: Novel):
        super().__init__()
        self.novel = novel

    def wrap(self, gen: Generator[Chapter, None, None]) -> Generator[Chapter, None, None]:
        # noinspection PyTypeChecker
        last_chap: Chapter = gen.__next__()
        for chapter in gen:
            if self.are_conflatable(last_chap, chapter):
                self.log.debug(f"Conflating chapter '{last_chap.title}' with '{chapter.title}'")
                self.conflate(last_chap, chapter)
            else:
                yield last_chap
                last_chap = chapter

    def _consume(self, chapter: Chapter) -> Chapter:
        raise NotImplementedError

    @staticmethod
    def are_conflatable(first: Chapter, second: Chapter) -> bool:
        pattern = re.compile(r'\w+')
        owns = pattern.findall(first.get_title())
        others = pattern.findall(second.get_title())
        for own, other in zip(owns, others):
            if own != other:
                return False
        return True

    @staticmethod
    def conflate(first: Chapter, second: Chapter):
        first.next_chapter_path = second.next_chapter_path
        first.content.append(second.content)
        # Delete the second chapter from the list of chapters from the book
        second.book.chapters.remove(second)
