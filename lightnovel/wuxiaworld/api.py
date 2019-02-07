import json
from typing import List
from bs4 import BeautifulSoup, Tag, NavigableString
from urllib3.util.url import parse_url
from lightnovel import ChapterEntry, Book, Novel, Chapter, LightNovelApi


class WuxiaWorld:
    host = 'https://www.wuxiaworld.com'
    name = 'wuxiaworld'


class WuxiaWorldChapterEntry(WuxiaWorld, ChapterEntry):
    pass


class WuxiaWorldBook(WuxiaWorld, Book):
    chapters: List[WuxiaWorldChapterEntry] = []


class WuxiaWorldNovel(WuxiaWorld, Novel):
    books: List[WuxiaWorldBook] = []
    tags: List[str] = []

    def _parse(self, document: BeautifulSoup) -> bool:
        head = document.select_one('head')
        json_data = json.loads(head.select_one('script[type="application/ld+json"]').text)
        self.title = json_data['name']
        self.log.debug("Novel title is: {}".format(self.title))
        url = json_data['potentialAction']['target']['urlTemplate']
        self.first_chapter_path = parse_url(url).path
        self.translator = json_data['author']['name']
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
        self.log.debug("Tags found: {}".format(tags))
        return tags

    def __extract_books(self, p15: Tag) -> List[WuxiaWorldBook]:
        books = []
        for book_html in p15.select('div#accordion div.panel.panel-default'):
            book = WuxiaWorldBook()
            book.title = book_html.select_one('a.collapsed').text.strip()
            self.log.debug("Book: {}".format(book.title))
            book.chapters = self.__extract_chapters(book_html)
            books.append(book)
        return books

    def __extract_chapters(self, book_html: Tag) -> List[WuxiaWorldChapterEntry]:
        chapters = []
        for chapter_html in book_html.select('div div li a'):
            chapter = WuxiaWorldChapterEntry()
            chapter.title = chapter_html.text.strip()
            chapter.path = chapter_html.get('href')
            chapters.append(chapter)
        self.log.debug("Chapters found: {}".format(len(chapters)))
        return chapters


class WuxiaWorldChapter(WuxiaWorld, Chapter):
    id = 0
    is_teaser = False
    content: Tag = None

    def _parse(self, document: BeautifulSoup):
        head = document.select_one('head')
        if head.select_one('meta[name="description"]').get('content') is None:
            self.success = False
            return
        else:
            self.success = True
        assert head.select_one('script[type="application/ld+json"]') is not None
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
        self.content = self._process_content(document.select_one('div.p-15 div.fr-view'), self.title)
        return True

    def _process_content(self, content: Tag, title: str) -> Tag:
        new_content = BeautifulSoup(features="html5lib")
        new_content.clear()
        tags_cnt = 0
        max_tags_cnt = 4
        # self.log.info(content.contents)
        for child in content.children:
            # self.log.debug('==== NEW CHILD ==== {}'.format(child))
            if type(child) == NavigableString:
                if len(child.strip('\n ')) == 0:
                    # self.log.debug("Empty string.")
                    pass
                else:
                    self.log.warning("Non-Empty string: '{}'.".format(child))
            elif type(child) == Tag:
                if child.name in ['p', 'div', 'a', 'blockquote']:
                    if len(child.text.strip('\n ')) == 0:
                        # self.log.debug("Empty paragraph.")
                        pass
                    else:
                        if child.text == '\nNext Chapter\n':
                            break
                        new_content.append(child.__copy__())
                        tags_cnt += 1
                        if tags_cnt <= max_tags_cnt and title in child.text.strip('\n '):
                            self.log.debug("Title found in paragraph. Discarding previous paragraphs.")
                            new_content = BeautifulSoup(features="html5lib")
                            new_content.clear()
                            tags_cnt = max_tags_cnt
                elif child.name == 'hr':
                    # self.log.debug('Rule reached.')
                    break
                else:
                    raise Exception("Unexpected tag name: {}".format(child))
            else:
                raise Exception("Unexpected type: {}".format(child))
        return new_content


class WuxiaWorldApi(WuxiaWorld, LightNovelApi):
    # Search: /api/novels/search?query=the&count=5
    def get_novel(self, url: str) -> WuxiaWorldNovel:
        return WuxiaWorldNovel(self._get_document(url))

    def get_chapter(self, url: str) -> WuxiaWorldChapter:
        return WuxiaWorldChapter(self._get_document(url))
