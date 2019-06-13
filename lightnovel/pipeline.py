import logging
import os
import re
from abc import ABC
from typing import Dict, Tuple
from typing import Generator, AnyStr, List
from zipfile import ZipFile

from lightnovel import Book
from lightnovel import Chapter, Novel
from util import slugify, sanitize_for_html, make_sure_dir_exists


class Pipeline(ABC):
    log: logging.Logger

    def __init__(self):
        self.log = logging.getLogger(self.__class__.__name__)

    def wrap(self, gen: Generator[Tuple[int, int, Chapter], None, None]) -> Generator[
        Tuple[int, int, Chapter], None, None]:
        raise NotImplementedError


class Parser(Pipeline):

    def wrap(self, gen: Generator[Tuple[Book, Chapter], None, None]) -> Generator[Tuple[Book, Chapter], None, None]:
        for book, chapter in gen:
            if not chapter.parse():
                self.log.warning(f"Failed parsing chapter {chapter}")
                return
            else:
                # TODO: Handle placeholder page for unreleased chapters
                # TODO: Delete cache for placeholder chapters
                self.log.info(f"Got chapter {chapter}")
                chapter.book = book
                book.chapters.append(chapter)
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
                last_chap.number = 1
                continue

            if self.are_conflatable(last_chap, chapter):
                self.log.debug(f"Conflating chapter '{last_chap.title}' with '{chapter.title}'")
                self.conflate(last_chap, chapter)
            else:  # Different chapter. Yield cached one and cache new one.
                self.log.debug(f"Cannot conflate the old chapter with chapter {chapter} '{chapter.get_title()}'")
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


class EpubFile(ABC):
    filepath: str = ''
    content: AnyStr = None

    def write_to(self, epub: ZipFile):
        epub.writestr(self.filepath, self.content)


class MimeTypeFile(EpubFile):
    filepath = 'mimetype'
    content = 'application/epub+zip'


class ContentFile(EpubFile):
    filepath = 'OEBPS/content.opf'
    metadata: str = ''
    manifest: List[str]
    spine: List[str]

    def __init__(self, novel: Novel, unique_id: str):
        self.manifest = []
        self.spine = []
        url = novel.get_url()
        title = sanitize_for_html(novel.title)
        rights = sanitize_for_html(novel.rights)
        name = sanitize_for_html(novel.name)
        tags = sanitize_for_html(' / '.join(['Web Novel', *novel.tags]))
        date = novel.date.strftime('%Y-%m-%d')
        description = sanitize_for_html(novel.description.text.strip('\xa0\n'))
        author = sanitize_for_html(novel.author)
        self.metadata = f'''<package xmlns="http://www.idpf.org/2007/opf" version="2.0" unique-identifier="{unique_id}">
  <metadata>
    <dc:identifier xmlns:dc="http://purl.org/dc/elements/1.1/" id="{unique_id}">{url}</dc:identifier>
    <dc:title xmlns:dc="http://purl.org/dc/elements/1.1/">{title}</dc:title>
    <dc:rights xmlns:dc="http://purl.org/dc/elements/1.1/">{rights}</dc:rights>
    <dc:publisher xmlns:dc="http://purl.org/dc/elements/1.1/">{name}</dc:publisher>
    <dc:subject xmlns:dc="http://purl.org/dc/elements/1.1/">{tags}</dc:subject>
    <dc:date xmlns:dc="http://purl.org/dc/elements/1.1/">{date}</dc:date>
    <dc:description xmlns:dc="http://purl.org/dc/elements/1.1/">{description}</dc:description>
    <dc:creator xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:opf="http://www.idpf.org/2007/opf" opf:file-as="{author}">{author}</dc:creator>
    <dc:language xmlns:dc="http://purl.org/dc/elements/1.1/">en</dc:language>
  </metadata>'''

    def add_file(self, unique_id: str, filename: str, mimetype: str, spine=True):
        self.manifest.append(
            f'<item id="{unique_id}" href="{filename.replace("OEBPS/", "")}" media-type="{mimetype}"/>')
        if spine:
            self.spine.append(f'<itemref idref="{unique_id}"/>')

    def compile(self):
        manifest = '\n    '.join(self.manifest)
        spine = '\n    '.join(self.spine)
        self.content = f'''<?xml version="1.0" encoding="utf-8" standalone="no"?>
{self.metadata}
  <manifest>
    {manifest}
  </manifest>
  <spine toc="ncxtoc">
    {spine}
  </spine>
</package>'''


class ContainerFile(EpubFile):
    filepath = 'META-INF/container.xml'
    content = f'''<?xml version="1.0" encoding="utf-8" standalone="no"?>
<odfc:container xmlns:odfc="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0">
  <odfc:rootfiles>
    <odfc:rootfile full-path="{ContentFile.filepath}" media-type="application/oebps-package+xml"/>
  </odfc:rootfiles>
</odfc:container>'''


class ChapterFile(EpubFile):
    id: str = ''

    def __init__(self, chapter: Chapter):
        book_n = chapter.book.number
        chapter_n = chapter.number
        self.filepath = f"OEBPS/{book_n}_{chapter_n}_{slugify(chapter.get_title())}.xhtml"
        self.id = f"chap_{book_n}_{chapter_n}"
        title = sanitize_for_html(chapter.get_title())
        self.content = f"""<?xml version="1.0" encoding="utf-8" standalone="no"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>{title}</title>
</head>
<body>
    <div class="chapter" lang="en">
        <div class="titlepage">
            <h2 class="title"><a id="{self.id}">{title}</a></h2>
        </div>
        {str(chapter.content)}
    </div>
</body>
</html>"""


class BookFile(EpubFile):
    id: str = ''

    def __init__(self, book: Book):
        self.filepath = f"OEBPS/{book.number}_{slugify(book.title)}.xhtml"
        self.id = f"book_{book.number}"
        title = sanitize_for_html(book.title)
        self.content = f"""<?xml version="1.0" encoding="utf-8" standalone="no"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>{title}</title>
</head>
<body>
    <div class="chapter" lang="en">
        <div class="titlepage">
            <h1 class="title"><a id="{self.id}">{title}</a></h1>
        </div>
    </div>
</body>
</html>"""


class TOC(EpubFile):
    filepath = 'OEBPS/toc.ncx'
    id = 'ncxtoc'
    opf_id: str = ''
    title: str = ''
    items: list
    cover: str = ''
    depth: int = 1
    id2title: Dict[str, str]
    id2filepath: Dict[str, str]
    structure: Dict[str, List[str]]

    def __init__(self, opf_id: str, title: str, cover='cover', depth=2):
        self.opf_id = opf_id
        self.title = title
        self.items = []
        self.cover = cover
        self.depth = depth
        self.id2title = {}
        self.id2filepath = {}
        self.structure = {}

    def add_book(self, book_id: str, title: str, filepath: str):
        self.structure[book_id] = []
        self.id2title[book_id] = sanitize_for_html(title)
        self.id2filepath[book_id] = filepath.replace("OEBPS/", "")

    def add_chapter(self, book_id: str, chapter_id: str, title: str, filepath: str):
        self.structure[book_id].append(chapter_id)
        self.id2title[chapter_id] = sanitize_for_html(title)
        self.id2filepath[chapter_id] = filepath.replace("OEBPS/", "")

    def compile(self):
        number = 0
        book_entries = []
        for book_id in self.structure:
            number += 1
            book_play_order = number
            chapter_entries = []
            for chapter_id in self.structure[book_id]:
                number += 1
                chapter_entries.append(f'''
      <ncx:navPoint id="navPoint-{number}" playOrder="{number}">
        <ncx:navLabel>
          <ncx:text>{self.id2title[chapter_id]}</ncx:text>
        </ncx:navLabel>
        <ncx:content src="{self.id2filepath[chapter_id]}"/>
      </ncx:navPoint>'''.strip())
            chapters_str = '\n'.join(chapter_entries)
            book_entries.append(f'''
    <ncx:navPoint id="navPoint-{book_play_order}" playOrder="{book_play_order}">
      <ncx:navLabel>
        <ncx:text>{self.id2title[book_id]}</ncx:text>
      </ncx:navLabel>
      <ncx:content src="{self.id2filepath[book_id]}"/>
      {chapters_str}
    </ncx:navPoint>''')
        books_str = '\n'.join(book_entries)
        self.content = f"""<?xml version="1.0" encoding="utf-8" standalone="no"?>
<!DOCTYPE ncx PUBLIC "-//NISO//DTD ncx 2005-1//EN" "http://www.daisy.org/z3986/2005/ncx-2005-1.dtd">
<ncx:ncx xmlns:ncx="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
  <ncx:head>
    <ncx:meta name="dtb:uid" content="{self.opf_id}"/>
    <ncx:meta name="dtb:depth" content="{self.depth}"/>
    <ncx:meta name="dtb:totalPageCount" content="0"/>
    <ncx:meta name="dtb:maxPageNumber" content="0"/>
  </ncx:head>
  <ncx:docTitle>
    <ncx:text>{sanitize_for_html(self.title)}</ncx:text>
  </ncx:docTitle>
  <ncx:navMap>
    {books_str}
  </ncx:navMap>
</ncx:ncx>"""


class EpubMaker(Output):
    def __init__(self, novel: Novel, out_path: str = 'out'):
        super().__init__(novel, 'epub', out_path)

    def wrap(self, gen: Generator[Tuple[Book, Chapter], None, None]) -> Generator[
        Tuple[Book, Chapter], None, None]:
        unique_id = slugify(self.novel.get_url())
        filepath = self.join_to_path(self.filename)
        with ZipFile(filepath, 'w') as epub:
            self.log.debug(f"Opened file '{filepath}'")
            MimeTypeFile().write_to(epub)
            ContainerFile().write_to(epub)
            content = ContentFile(self.novel, unique_id)
            toc = TOC(self.novel.get_url(), self.novel.title)
            content.add_file(toc.id, toc.filepath, 'application/x-dtbncx+xml', False)

            try:
                last_book = None
                for book, chapter in gen:
                    self.log.debug(f"Adding chapter {chapter} to epub")
                    if book != last_book:  # New book
                        last_book = book
                        book = chapter.book
                        book_file = BookFile(book)
                        book_file.write_to(epub)
                        toc.add_book(book_file.id, book.title, book_file.filepath)
                        content.add_file(book_file.id, book_file.filepath, 'application/xhtml+xml')
                        self.log.debug(f"Saved book {book} to ({book_file.id}): {book_file.filepath}")
                    chapter_file = ChapterFile(chapter)
                    chapter_file.write_to(epub)
                    toc.add_chapter(book_file.id, chapter_file.id, chapter.get_title(), chapter_file.filepath)
                    content.add_file(chapter_file.id, chapter_file.filepath, 'application/xhtml+xml')
                    self.log.debug(
                        f"Saved chapter {chapter} to ({chapter_file.id}): {chapter_file.filepath}")
                    yield book, chapter
            finally:
                content.compile()
                content.write_to(epub)
                toc.compile()
                toc.write_to(epub)


class DeleteChapters(Pipeline):
    def wrap(self, gen: Generator[Tuple[Book, Chapter], None, None]):
        for _, chapter in gen:
            self.delete_chapter(chapter)
            self.log.debug(f"Deleted chapter {chapter}")

    @staticmethod
    def delete_chapter(chapter: Chapter):
        chapter.book.chapters.remove(chapter)
        del chapter
