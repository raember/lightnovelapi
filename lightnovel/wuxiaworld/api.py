import html
import json
from datetime import datetime
from typing import List

# noinspection PyProtectedMember
from bs4 import BeautifulSoup, Tag, NavigableString
from urllib3.util.url import parse_url

from lightnovel import ChapterEntry, Book, Novel, Chapter, LightNovelApi, SearchEntry
from lightnovel.util import slugify


class WuxiaWorld:
    host = 'https://www.wuxiaworld.com'
    name = 'WuxiaWorld'


class WuxiaWorldChapterEntry(WuxiaWorld, ChapterEntry):
    pass


class WuxiaWorldBook(WuxiaWorld, Book):
    chapter_entries: List[WuxiaWorldChapterEntry] = []
    chapters: List['WuxiaWorldChapter'] = []


class WuxiaWorldSearchEntry(WuxiaWorld, SearchEntry):
    id: int
    name: str
    slug: str
    cover_url: str
    abbreviation: str
    synopsis: str
    language: str
    time_created: datetime
    status: int
    chapter_count: int
    tags: List[str]

    def __init__(self, json_data: dict):
        super().__init__()
        self.id = int(json_data['id'])
        self.name = json_data['name']
        self.slug = json_data['slug']
        self.cover_url = json_data['coverUrl']
        self.abbreviation = json_data['abbreviation']
        self.synopsis = json_data['synopsis']
        self.language = json_data['language']
        self.time_created = datetime.utcfromtimestamp(float(json_data['timeCreated']))
        self.status = int(json_data['status'])
        self.chapter_count = int(json_data['chapterCount'])
        self.tags = list(json_data['tags'])
        self.title = self.name
        self.path = f"novel/{self.slug}"


class WuxiaWorldNovel(WuxiaWorld, Novel):
    books: List[WuxiaWorldBook] = []

    def _parse(self, document: BeautifulSoup) -> bool:
        head = document.select_one('head')
        json_data = json.loads(head.select_one('script[type="application/ld+json"]').text)
        self.title = json_data['name']
        self.log.debug(f"Novel title is: {self.title}")
        url = json_data['potentialAction']['target']['urlTemplate']
        self.first_chapter_path = parse_url(url).path
        self.author = json_data['author']['name']  # Usually only translator is given
        self.translator = self.author
        self.rights = html.unescape(document.select_one('p.legal').getText())
        self.date = datetime.fromisoformat(json_data['datePublished'])
        self.img_url = head.select_one('meta[property="og:image"]').get('content')
        url = head.select_one('meta[property="og:url"]').get('content')
        self.path = parse_url(url).path
        p15 = document.select_one('div.p-15')
        self.tags = self.__extract_tags(p15)
        self.description = p15.select('div.fr-view')[1]
        self.books = self.__extract_books(p15)
        return True

    def __extract_tags(self, p15: Tag) -> List[str]:
        tags = []
        for tag_html in p15.select('div.media.media-novel-index div.media-body div.tags a'):
            tag = tag_html.text.strip()
            tags.append(tag)
        self.log.debug(f"Tags found: {tags}")
        return tags

    def __extract_books(self, p15: Tag) -> List[WuxiaWorldBook]:
        books = []
        for book_html in p15.select('div#accordion div.panel.panel-default'):
            book = WuxiaWorldBook()
            book.novel = self
            book.title = book_html.select_one('a.collapsed').text.strip()
            self.log.debug(f"Book: {book.title}")
            book.chapter_entries = self.__extract_chapters(book_html)
            books.append(book)
        return books

    def __extract_chapters(self, book_html: Tag) -> List[WuxiaWorldChapterEntry]:
        chapters = []
        for chapter_html in book_html.select('div div li a'):
            chapter = WuxiaWorldChapterEntry()
            chapter.title = chapter_html.text.strip()
            chapter.path = chapter_html.get('href')
            chapters.append(chapter)
        self.log.debug(f"Chapters found: {len(chapters)}")
        return chapters


class WuxiaWorldChapter(WuxiaWorld, Chapter):
    def is_complete(self) -> bool:
        return self.document.select_one('head meta[name="description"]').has_attr('content')

    id = 0
    is_teaser = False
    content: Tag = None

    def _parse(self, document: BeautifulSoup) -> bool:
        head = document.select_one('head')
        url = parse_url(head.select_one('link[rel="canonical"]').get('href'))
        if url.path == '/Error':
            return False
        if self.is_complete():
            json_str = head.select_one('script[type="application/ld+json"]').text
            json_data = json.loads(json_str)
            self.translator = json_data['author']['name']
            # self.title = head.select_one('meta[property=og:title]').get('content').replace('  ', ' ')
            url = head.select_one('meta[property="og:url"]').get('content')
            self.path = parse_url(url).path
            for script_tag in head.select('script'):
                script = script_tag.text.strip('\n \t;')
                if script.startswith('var CHAPTER = '):
                    json_data = json.loads(script[14:])
                    break
            self.title = json_data['name']
            self.id = int(json_data['id'])
            self.is_teaser = json_data['isTeaser']
            self.previous_chapter_path = json_data['prevChapter']
            self.next_chapter_path = json_data['nextChapter']
            if self.title == '':
                self.log.warning("Couldn't extract data from CHAPTER variable.")
            self.content = document.select_one('div.p-15 div.fr-view')
        return True

    def clean_content(self):
        bs = BeautifulSoup(features="html5lib")
        new_content = bs.new_tag('div')
        new_content.clear()
        tags_cnt = 0
        max_tags_cnt = 4
        for child in self.content.children:
            if isinstance(child, NavigableString):
                if len(child.strip('\n  ')) == 0:
                    # self.log.debug("Empty string.")
                    pass
                else:
                    self.log.warning(f"Non-Empty string: '{child}'.")
            elif isinstance(child, Tag):
                # ['p', 'div', 'a', 'blockquote', 'ol', 'ul', 'h1', 'h2', 'h3', 'h4', 'h5']
                if child.name == 'blockquote':  # Blockquotes have to have a paragraph within
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
                        title_str = self.get_title()
                        if tags_cnt <= max_tags_cnt and title_str != '' and title_str in child.text.strip('\n '):
                            self.log.debug("Title found in paragraph. Discarding previous paragraphs.")
                            new_content.clear()
                            tags_cnt = max_tags_cnt
                elif child.name == 'hr':
                    new_content.append(child)
                elif child.name == 'a':
                    continue
                else:
                    raise Exception(f"Unexpected tag name: {child}")
            else:
                raise Exception(f"Unexpected type: {child}")
        self.content = new_content

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


class WuxiaWorldApi(WuxiaWorld, LightNovelApi):
    def get_novel(self, url: str) -> WuxiaWorldNovel:
        return WuxiaWorldNovel(self._get_document(url))

    def get_chapter(self, url: str) -> WuxiaWorldChapter:
        return WuxiaWorldChapter(self._get_document(url))

    def search(self, title_or_abbr: str, count: int = 5) -> List[WuxiaWorldSearchEntry]:
        """
        Searches for a novel by title or abbreviation.
        :param title_or_abbr: The title to search for.
        :param count: The maximum amount of results.
        :return: A list of SearchEntry.
        """
        title_or_abbr = slugify(title_or_abbr, lowercase=False)
        # TODO: Respect robots.txt and don't use /api/* calls. Instead, use https://www.wuxiaworld.com/sitemap/novels
        data = self._get(
            f"https://www.wuxiaworld.com/api/novels/search?query={title_or_abbr}&count={count}",
            use_cache=False,
            headers={'Accept': 'application/json'}
        ).json()
        assert data['result']
        entries = []
        for item in data['items']:
            entries.append(WuxiaWorldSearchEntry(item))
        return entries
