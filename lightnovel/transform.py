import logging

from lightnovel import Novel


class Transformer:
    log: logging.Logger
    novel: Novel = None

    def __init__(self, novel: Novel):
        self.log = logging.getLogger(self.__class__.__name__)
        self.novel = novel
        if self.novel.image is None:
            self.log.warning(f"No image found in Novel '{self.novel.title}'")
        if len(self.novel.books) == 0:
            self.log.error(f"No books found in Novel '{self.novel.title}'")
        else:
            for book in self.novel.books:
                n_chapters = len(book.chapters)
                n_chapter_entries = len(book.chapter_entries)
                if n_chapters == 0 or n_chapters != n_chapter_entries:
                    self.log.warning(f"Number of chapters inside book '{book.title}' in Novel '{self.novel.title}' "
                                     f"is unexpectedly {n_chapters}/{n_chapter_entries}")

    def export(self, path: str):
        raise NotImplementedError

