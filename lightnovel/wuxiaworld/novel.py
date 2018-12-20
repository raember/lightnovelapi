import json
from lightnovel.api import Novel, ChapterEntry, Book
from typing import List
from bs4 import BeautifulSoup, Tag
from urllib3.util.url import parse_url
from . import WuxiaWorld


class WuxiaWorldChapterEntry(WuxiaWorld, ChapterEntry):
    pass


class WuxiaWorldBook(WuxiaWorld, Book):
    chapters: List[WuxiaWorldChapterEntry] = []


class WuxiaWorldNovel(WuxiaWorld, Novel):
    books: List[WuxiaWorldBook] = []
    tags: List[str] = []

    def _parse(self, document: BeautifulSoup):
        head = document.select_one('head')
        json_data = json.loads(head.select_one('script[type=application/ld+json]').text)
        self.title = json_data['name']
        self.log.debug("Novel title is: {}".format(self.title))
        url = json_data['potentialAction']['target']['urlTemplate']
        self.first_chapter_path = parse_url(url).path
        self.translator = json_data['author']['name']
        self.img_url = head.select_one('meta[property=og:image]').get('content')
        url = head.select_one('meta[property=og:url]').get('content')
        self.path = parse_url(url).path
        p15 = document.select_one('div.p-15')
        self.tags = self.__extract_tags(p15)
        self.description = p15.select('div.fr-view')[1]
        self.books = self.__extract_books(p15)

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

