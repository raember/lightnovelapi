import logging
import os
import re
from abc import ABC
from typing import Generator, AnyStr
from typing import Tuple

# from epub import EpubFile, BookFile, ChapterFile
from PIL.Image import Image
from ebooklib.epub import EpubBook, EpubNcx, EpubNav, EpubHtml, Section, write_epub

from lightnovel import Book
from lightnovel import Chapter, Novel
from util import slugify, make_sure_dir_exists, Proxy


class Pipeline(ABC):
    log: logging.Logger

    def __init__(self):
        self.log = logging.getLogger(self.__class__.__name__)

    def wrap(self, gen: Generator[Tuple[int, int, Chapter], None, None]) -> Generator[
        Tuple[int, int, Chapter], None, None]:
        raise NotImplementedError


class Parser(Pipeline):
    def __init__(self, proxy: Proxy):
        super().__init__()
        self.proxy = proxy

    def wrap(self, gen: Generator[Tuple[Book, Chapter], None, None]) -> Generator[Tuple[Book, Chapter], None, None]:
        for book, chapter in gen:
            if not chapter.parse():
                self.log.warning(f"Failed parsing chapter {chapter}")
                return
            else:
                if chapter.is_complete():
                    self.log.info(f"Got chapter {chapter}")
                    del chapter.document  # No need to keep that much data in memory
                    chapter.book = book
                    book.chapters.append(chapter)
                    yield book, chapter
                else:
                    self.log.info("Chapter not released yet.")
                    self.proxy.delete_from_cache()


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
                last_chap.number = 1
                continue

            if self.are_conflatable(last_chap, chapter):
                self.log.debug(f"Conflating chapter '{last_chap.title}' with '{chapter.title}'")
                self.conflate(last_chap, chapter)
            else:  # Different chapter. Yield cached one and cache new one.
                self.log.debug(f"Cannot conflate the old chapter ({last_chap}) with chapter {chapter}")
                yield book, last_chap
                last_chap = chapter
                last_chap.number += 1
        self.log.debug("Source generator finished. Yielding last chapter")
        yield last_book, last_chap

    @staticmethod
    def are_conflatable(first: Chapter, second: Chapter) -> bool:
        pattern = re.compile(r'[\w\d]+')
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
        DeleteChapters.delete_chapter(second)


class Output(Pipeline):

    def __init__(self, novel: Novel, ext: str, out_path: str = 'out'):
        super().__init__()
        self.novel = novel
        self.ext = ext
        self.out_path = out_path
        self.slug_title = slugify(novel.title, lowercase=False)
        self.filename = f"{self.slug_title}.{self.ext}"
        self.path = os.path.join(out_path, self.novel.name, self.slug_title, ext)
        make_sure_dir_exists(self.path)

    def join_to_path(self, *paths: str) -> str:
        return os.path.join(self.path, *paths)


class EpubMaker(Output):
    def __init__(self, novel: Novel, out_path: str = 'out'):
        super().__init__(novel, 'epub', out_path)

    def wrap(self, gen: Generator[Tuple[Book, Chapter], None, None]) -> Generator[
        Tuple[Book, Chapter], None, None]:
        unique_id = slugify(self.novel.title)
        filepath = self.join_to_path(self.filename)

        epub = EpubBook()
        epub.set_title(self.novel.title)
        epub.set_identifier(self.novel.get_url())
        lang = self.novel.language
        epub.set_language(lang)
        epub.add_metadata('DC', 'rights', self.novel.rights)
        epub.add_metadata('DC', 'publisher', self.novel.name)
        epub.add_metadata('DC', 'subject', ' / '.join(['Web Novel', *self.novel.tags]))
        epub.add_metadata('DC', 'date', self.novel.date.strftime('%Y-%m-%d'))
        epub.add_metadata('DC', 'description', self.novel.description.text)
        epub.add_author(self.novel.author)
        epub.add_author(self.novel.translator, role='translator', uid='translator')
        cover_filename, img_data = self.__prepare_image(self.novel.image, 'cover-image')
        if cover_filename != '':
            epub.set_cover(cover_filename, img_data)

        try:
            last_book = None
            for book, chapter in gen:
                self.log.debug(f"Adding chapter {chapter} to epub")
                if book != last_book:  # New book
                    last_book = book
                    book = chapter.book
                    book_file = EpubHtml(
                        title=book.title,
                        file_name=f"{book.number}_{slugify(book.title)}.xhtml",
                        lang=lang
                    )
                    book_file.content = f'<h1>{book.title}</h1>'
                    epub.add_item(book_file)
                    epub.toc.append(Section(book.title))
                    epub.toc.append(book_file)
                    epub.spine.append(book_file)
                    # book_file = BookFile(book)
                    # epub.add_book(book_file)
                    self.log.debug(f"Saved book {book} to ({book_file.id}): {book_file.file_name}")
                chapter_file = EpubHtml(
                    title=chapter.title,
                    file_name=f"{book.number}_{chapter.number}_{slugify(chapter.get_title())}.xhtml",
                    lang=chapter.language
                )
                chapter_file.content = f"""<head>
    <title>{chapter.get_title()}</title>
</head>
<body>
    <div class="chapter" lang="en">
        <div class="titlepage">
            <h2 class="title"><a id="{chapter_file.id}">{chapter.get_title()}</a></h2>
        </div>
        {str(chapter.content)}
    </div>
</body>"""
                epub.add_item(chapter_file)
                epub.toc.append(chapter_file)  # TODO: Make hierarchical TOC
                epub.spine.append(chapter_file)
                # chapter_file = ChapterFile(chapter)
                # epub.add_chapter(book_file, chapter_file)
                self.log.debug(
                    f"Saved chapter {chapter} to ({chapter_file.id}): {chapter_file.file_name}")
                yield book, chapter
        finally:
            epub.add_item(EpubNcx())
            epub.add_item(EpubNav())
            write_epub(filepath, epub, {})
            self.log.info("Finished creating epub")

        # with EpubFile(filepath, unique_id, self.novel.title, self.novel.language, identifier=self.novel.get_url(),
        #               rights=self.novel.rights, publisher=self.novel.name,
        #               subject=' / '.join(['Web Novel', *self.novel.tags]), date=self.novel.date,
        #               description=self.novel.description.text, creator=self.novel.author, cover_image=self.novel.image,
        #               mode='w') as epub:
        #     self.log.debug(f"Opened file '{filepath}'")
        #     last_book = None
        #     for book, chapter in gen:
        #         self.log.debug(f"Adding chapter {chapter} to epub")
        #         if book != last_book:  # New book
        #             last_book = book
        #             book = chapter.book
        #             book_file = BookFile(book)
        #             epub.add_book(book_file)
        #             self.log.debug(f"Saved book {book} to ({book_file.unique_id}): {book_file.filepath}")
        #         chapter_file = ChapterFile(chapter)
        #         epub.add_chapter(book_file, chapter_file)
        #         self.log.debug(
        #             f"Saved chapter {chapter} to ({chapter_file.unique_id}): {chapter_file.filepath}")
        #         yield book, chapter

    def __prepare_image(self, img: Image, filename: str) -> Tuple[str, AnyStr]:
        ext = img.format.lower()
        if ext not in ['png', 'jpeg', 'jpg', 'gif', 'svg+xml']:  # TODO: Write tests for these.
            self.log.error(f"Image type {img.format} is not supported.")
            return "", ""
        filename = f"{filename}.{ext}"
        tmp_img_filename = '_tmp_img'
        img.save(tmp_img_filename, format=img.format)
        with open(tmp_img_filename, 'rb') as f:
            content = f.read()
        os.remove(tmp_img_filename)
        return filename, content


class DeleteChapters(Pipeline):
    def wrap(self, gen: Generator[Tuple[Book, Chapter], None, None]):
        for _, chapter in gen:
            self.delete_chapter(chapter)
            self.log.debug(f"Deleted chapter {chapter}")

    @staticmethod
    def delete_chapter(chapter: Chapter):
        chapter.book.chapters.remove(chapter)
        del chapter
