import json
from lightnovel.log_class import LogBase
from typing import List
from bs4 import BeautifulSoup, Tag
from urllib3.util.url import parse_url


class WuxiaWorldChapterLink:
    title = ''
    path = ''


class WuxiaWorldBook:
    title = ''
    chapters: List[WuxiaWorldChapterLink] = []


class WuxiaWorldNovel(LogBase):
    title = ''
    translator = ''
    tags: List[str] = []
    description: Tag = None
    books: List[WuxiaWorldBook] = []
    first_chapter_path = ''
    img_url = 'https://cdn.wuxiaworld.com/images/covers/'
    path = 'https://www.wuxiaworld.com/novel/'

    def __init__(self, bs: BeautifulSoup):
        super().__init__()
        self.log.debug('Extracting data from html.')
        head = bs.select_one('head')
        json_str = head.select_one('script[type=application/ld+json]').text
        json_data = json.loads(json_str)
        self.title = json_data['name']
        self.log.debug("Novel title is: {}".format(self.title))
        url = json_data['potentialAction']['target']['urlTemplate']
        self.first_chapter_path = parse_url(url).path
        self.translator = json_data['author']['name']
        self.img_url = head.select_one('meta[property=og:image]').get('content')
        url = head.select_one('meta[property=og:url]').get('content')
        self.path = parse_url(url).path
        p15 = bs.select_one('div.p-15')
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

    def __extract_chapters(self, book_html: Tag) -> List[WuxiaWorldChapterLink]:
        chapters = []
        for chapter_html in book_html.select('div div li a'):
            chapter = WuxiaWorldChapterLink()
            chapter.title = chapter_html.text.strip()
            chapter.path = chapter_html.get('href')
            chapters.append(chapter)
        self.log.debug("Chapters found: {}".format(len(chapters)))
        return chapters
