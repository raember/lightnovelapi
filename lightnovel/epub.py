import logging
import os
from abc import ABC
from datetime import datetime
from typing import AnyStr, List
from typing import Dict
from zipfile import ZipFile, ZIP_STORED

from PIL.Image import Image
# noinspection PyProtectedMember
from bs4 import BeautifulSoup, Tag, PageElement

from api import Book, Chapter
from util import slugify, sanitize_for_html


class EpubEntry(ABC):
    log: logging.Logger
    filepath: str = ''
    content: AnyStr = None
    mime_type = ''
    ext = ''
    unique_id = ''

    def __init__(self):
        self.log = logging.getLogger(self.__class__.__name__)

    @staticmethod
    def create_soup(version=1.0, encoding='utf-8', standalone=False) -> BeautifulSoup:
        return BeautifulSoup(
            f'<?xml version="{version}" encoding="{encoding}" standalone="{"yes" if standalone else "no"}"?>',
            'html.parser'
        )


class HtmlFile(EpubEntry, ABC):
    mime_type = 'application/html'
    ext = 'html'
    content: BeautifulSoup = None


class XHtmlFile(EpubEntry, ABC):
    mime_type = 'application/xhtml+xml'
    ext = 'xhtml'
    content: BeautifulSoup = None


class CssFile(EpubEntry, ABC):
    mime_type = 'text/css'
    ext = 'css'


class OpfFile(EpubEntry, ABC):
    mime_type = 'application/oebps-package+xml'
    ext = 'opf'
    content: BeautifulSoup = None


class NcxFile(EpubEntry, ABC):
    mime_type = 'application/x-dtbncx+xml'
    ext = 'ncx'
    content: BeautifulSoup = None


class MimeTypeFile(EpubEntry):
    filepath = 'mimetype'
    content = 'application/epub+zip'


class ContentFile(OpfFile):
    filepath = 'OEBPS/content.opf'
    content: BeautifulSoup
    package: BeautifulSoup
    metadata: BeautifulSoup
    manifest: BeautifulSoup
    spine: BeautifulSoup

    def __init__(self, unique_id: str):
        super().__init__()
        self.unique_id = unique_id
        self.content = self.create_soup(standalone=True)

        self.package = self.content.new_tag('package', attrs={
            'xmlns:dc': "http://purl.org/dc/elements/1.1/",
            # 'xmlns:opf': "http://www.idpf.org/2007/opf",
            'xmlns': "http://www.idpf.org/2007/opf",
            'version': 2.0,
            'unique-identifier': unique_id
        })
        self.metadata = self.content.new_tag('metadata')
        self.manifest = self.content.new_tag('manifest')
        self.spine = self.content.new_tag('spine')

        self.content.append(self.package)
        self.package.append(self.metadata)
        self.package.append(self.manifest)
        self.package.append(self.spine)

    @property
    def identifier(self) -> str:
        return self.__get_metadata_tag('identifier').contents[0]

    @identifier.setter
    def identifier(self, identifier: str):
        tag = self.__get_metadata_tag('identifier', self.content.new_string(identifier))
        tag['id'] = self.unique_id

    @property
    def title(self) -> str:
        return self.__get_metadata_tag('title').contents[0]

    @title.setter
    def title(self, title: str):
        self.__get_metadata_tag('title', self.content.new_string(title))

    @property
    def rights(self) -> str:
        return self.__get_metadata_tag('rights').contents[0]

    @rights.setter
    def rights(self, rights: str):
        self.__get_metadata_tag('rights', self.content.new_string(rights))

    @property
    def publisher(self) -> str:
        return self.__get_metadata_tag('publisher').contents[0]

    @publisher.setter
    def publisher(self, publisher: str):
        self.__get_metadata_tag('publisher', self.content.new_string(publisher))

    @property
    def subject(self) -> str:
        return self.__get_metadata_tag('subject').contents[0]

    @subject.setter
    def subject(self, subject: str):
        self.__get_metadata_tag('subject', self.content.new_string(subject))

    @property
    def date(self) -> datetime:
        return datetime.fromisoformat(self.__get_metadata_tag('date').contents[0])

    @date.setter
    def date(self, date: datetime):
        self.__get_metadata_tag('date', self.content.new_string(date.strftime('%Y-%m-%d')))

    @property
    def description(self) -> str:
        return self.__get_metadata_tag('description').contents[0]

    @description.setter
    def description(self, description: str):
        self.__get_metadata_tag('description', self.content.new_string(description))

    @property
    def creator(self) -> str:
        return self.__get_metadata_tag('creator').contents[0]

    @creator.setter
    def creator(self, creator: str):
        tag = self.__get_metadata_tag('creator', self.content.new_string(creator))
        tag['xmlns:opf'] = "http://www.idpf.org/2007/opf"
        tag['opf:file-as'] = creator

    @property
    def language(self) -> str:
        return self.__get_metadata_tag('language').contents[0]

    @language.setter
    def language(self, language: str):
        self.__get_metadata_tag('language', self.content.new_string(language))

    def __get_metadata_tag(self, key: str, default: PageElement = None, **kwargs) -> Tag:
        try:
            tag = self.metadata.find(f'dc\\:{key}')
        except Exception as e:
            self.log.error(f"BeautifulSoup is bitching around ({e})")
            tag = None
        if tag is None:
            attrs = {'xmlns': "http://purl.org/dc/elements/1.1/"}
            attrs.update(kwargs)
            tag = self.content.new_tag(key, nsprefix='dc', attrs=attrs)
            tag.contents = [default]
            self.metadata.append(tag)
        return tag

    def add_file(self, file: EpubEntry, **kwargs):
        self.manifest.append(self.__create_manifest_entry(file, **kwargs))
        self.spine.append(self.__create_spine_entry(file.unique_id))

    def __create_manifest_entry(self, file: EpubEntry, **kwargs) -> BeautifulSoup:
        attrs = {
            'id': file.unique_id,
            'href': file.filepath.replace("OEBPS/", ""),
            'media-type': file.mime_type
        }
        attrs.update(kwargs)
        manifest_entry = self.content.new_tag('item', attrs=attrs)
        return manifest_entry

    def __create_spine_entry(self, unique_id: str, **kwargs):
        attrs = {'idref': unique_id}
        attrs.update(kwargs)
        # noinspection SpellCheckingInspection
        spine_entry = self.content.new_tag('itemref', attrs=attrs)
        return spine_entry

    def register_toc(self, toc: 'TOC'):
        self.manifest.append(self.__create_manifest_entry(toc))
        self.spine['toc'] = toc.unique_id

    def register_cover_image(self, image: 'ImageFile', cover: 'CoverFile'):
        # self.add_file(image)
        self.manifest.append(self.__create_manifest_entry(image))
        self.add_file(cover)
        # self.manifest.append(self.__create_manifest_entry(cover))
        # self.spine.append(self.__create_spine_entry(cover.unique_id, linear='yes'))
        self.metadata.append(self.content.new_tag('meta', attrs={
            'name': cover.unique_id,
            'content': image.unique_id
        }))


class ContainerFile(XHtmlFile):
    filepath = 'META-INF/container.xml'
    # noinspection SpellCheckingInspection
    content = f'''<?xml version="1.0" encoding="utf-8" standalone="no"?>
<odfc:container xmlns:odfc="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0">
  <odfc:rootfiles>
    <odfc:rootfile full-path="{ContentFile.filepath}" media-type="application/oebps-package+xml"/>
  </odfc:rootfiles>
</odfc:container>'''


class ChapterFile(XHtmlFile):
    def __init__(self, chapter: Chapter):
        super(ChapterFile, self).__init__()
        self.chapter = chapter
        book_n = chapter.book.number
        chapter_n = chapter.index
        self.sanitized_title = sanitize_for_html(chapter.extract_clean_title())
        self.filepath = f"OEBPS/{book_n}_{chapter_n}_{slugify(chapter.extract_clean_title())}.xhtml"
        self.unique_id = f"chap_{book_n}_{chapter_n}"
        title = sanitize_for_html(chapter.extract_clean_title())
        # noinspection SpellCheckingInspection
        self.content = BeautifulSoup(f"""<?xml version="1.0" encoding="utf-8" standalone="no"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>{title}</title>
</head>
<body>
    <div class="chapter" lang="en">
        <div class="titlepage">
            <h2 class="title"><a id="{self.unique_id}">{title}</a></h2>
        </div>
        {str(chapter.content)}
    </div>
</body>
</html>""", 'html.parser')


class BookFile(XHtmlFile):
    def __init__(self, book: Book):
        super(BookFile, self).__init__()
        self.book = book
        self.filepath = f"OEBPS/{book.index}_{slugify(book.title)}.{self.ext}"
        self.unique_id = f"book_{book.index}"
        title = sanitize_for_html(book.title)
        # noinspection SpellCheckingInspection
        self.content = BeautifulSoup(f"""<?xml version="1.0" encoding="utf-8" standalone="no"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>{title}</title>
</head>
<body>
    <div class="chapter" lang="en">
        <div class="titlepage">
            <h1 class="title"><a id="{self.unique_id}">{title}</a></h1>
        </div>
    </div>
</body>
</html>""", 'html.parser')


class TOC(NcxFile):
    filepath = 'OEBPS/toc.ncx'
    unique_id = 'ncxtoc'
    opf_id: str = ''
    title: str = ''
    content: str = ""
    items: list
    depth: int = 1
    id2title: Dict[str, str]
    id2filepath: Dict[str, str]
    structure: Dict[str, List[str]]

    def __init__(self, opf_id: str, title: str, depth=2):  # TODO: Rework toc
        super().__init__()
        self.opf_id = opf_id
        self.title = sanitize_for_html(title)
        self.items = []
        self.depth = depth
        self.id2title = {}
        self.id2filepath = {}
        self.structure = {}

    def add_book(self, book_id: str, title: str, filepath: str):
        self.structure[book_id] = []
        self.id2title[book_id] = sanitize_for_html(title)
        self.id2filepath[book_id] = filepath.replace("OEBPS/", "")

    def add_chapter(self, book: BookFile, chapter: ChapterFile):
        self.structure[book.unique_id].append(chapter.unique_id)
        self.id2title[chapter.unique_id] = chapter.sanitized_title
        self.id2filepath[chapter.unique_id] = chapter.filepath.replace("OEBPS/", "")

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
            chapters_str = '      ' + '      \n'.join(chapter_entries)
            book_entries.append(f'''
    <ncx:navPoint id="navPoint-{book_play_order}" playOrder="{book_play_order}">
      <ncx:navLabel>
        <ncx:text>{self.id2title[book_id]}</ncx:text>
      </ncx:navLabel>
      <ncx:content src="{self.id2filepath[book_id]}"/>
      {chapters_str}
    </ncx:navPoint>''')
        books_str = '    ' + '\n    '.join(book_entries)
        # noinspection SpellCheckingInspection
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


class ImageFile(EpubEntry):
    mime_type = 'image/*'

    def __init__(self, filename: str, image: Image, unique_id: str):
        super().__init__()
        ext = image.format.lower()
        if ext not in ['png', 'jpeg', 'jpg', 'gif', 'svg+xml']:  # TODO: Write tests for these.
            self.log.error(f"Image type {image.format} is not supported.")
            return
        self.filepath = f"OEBPS/{filename}.{ext}"
        self.mimetype = f"image/{ext}"
        self.unique_id = unique_id
        tmp_img_filename = '_tmp_img'
        image.save(tmp_img_filename, format=image.format)
        with open(tmp_img_filename, 'rb') as f:
            self.content = f.read()
        os.remove(tmp_img_filename)


class CoverFile(XHtmlFile):
    filepath = 'OEBPS/cover.xhtml'

    def __init__(self, img: ImageFile):
        super().__init__()
        self.unique_id = 'cover'
        self.content = BeautifulSoup(f'''<?xml version="1.0" encoding="utf-8" standalone="no"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>Cover</title>
    <style type="text/css">img {{ max-width: 100%; }}</style>
</head>
<body>
    <div id="{img.unique_id}">
        <img src="{img.filepath.replace("OEBPS/", "")}" alt=""/>
    </div>
</body>
</html>''', 'html.parser')


class EpubFile(ZipFile):
    def __init__(self, file: str, unique_id: str, title: str, language: str, identifier: str, rights: str = None,
                 publisher: str = None, subject: str = None, date: datetime = None, description: str = None,
                 creator: str = None, cover_image: Image = None, toc_depth=2, mode="r", compression=ZIP_STORED,
                 allow_zip64=True, compress_level=None):
        super().__init__(file, mode, compression, allow_zip64, compress_level)
        mimetype = MimeTypeFile()
        self.__write_file(mimetype)
        container = ContainerFile()
        self.__write_file(container)
        self.toc = TOC(identifier, title, toc_depth)
        self.content = ContentFile(unique_id)
        self.content.title = title
        self.content.language = language
        self.content.identifier = identifier
        if rights is not None:
            self.content.rights = rights
        if publisher is not None:
            self.content.publisher = publisher
        if subject is not None:
            self.content.subject = subject
        if date is not None:
            self.content.date = date
        if description is not None:
            self.content.description = description
        if creator is not None:
            self.content.creator = creator
        self.content.register_toc(self.toc)

        if cover_image is not None:
            image = ImageFile('cover', cover_image, 'cover-image')
            cover = CoverFile(image)
            self.content.register_cover_image(image, cover)
            self.__write_file(image)
            self.__write_file(cover)

    def __write_file(self, file: EpubEntry):
        if isinstance(file.content, BeautifulSoup):
            content = file.content.prettify()
        else:
            content = file.content
        self.writestr(file.filepath, content)

    def add_book(self, book_file: BookFile):
        self.__write_file(book_file)
        self.content.add_file(book_file)
        self.toc.add_book(book_file.unique_id, book_file.book.title, book_file.filepath)

    def add_chapter(self, book: BookFile, chapter: ChapterFile):
        self.__write_file(chapter)
        self.content.add_file(chapter)
        self.toc.add_chapter(book, chapter)

    def __enter__(self):
        return self

    def __exit__(self, exit_type, value, traceback):
        self.toc.compile()
        self.writestr(self.toc.filepath, self.toc.content)
        self.writestr(self.content.filepath, self.content.content.prettify())
        self.close()
