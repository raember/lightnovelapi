import logging
import os
import shutil
import time
from abc import ABC
from typing import List, Tuple

from bs4 import Tag, BeautifulSoup
from urllib3.util import parse_url

import lightnovel.util.proxy as proxyutil
import lightnovel.util.text as textutil


class LightNovelEntity:
    host = ''

    def __init__(self):
        self.log = logging.getLogger(self.__class__.__name__)

    def get_url(self, path=''):
        return self.host + path


class LightNovelPage(LightNovelEntity):
    title = ''
    path = ''
    document = None
    success = False
    name = 'generic'

    def __init__(self, document: BeautifulSoup):
        super().__init__()
        self.document = document

    def parse(self, document: BeautifulSoup = None) -> bool:
        if not document:
            document = self.document
        try:
            self.success = self._parse(document)
        except Exception as e:
            self.log.error(e)
            self.success = False
        finally:
            return self.success

    def _parse(self, document: BeautifulSoup) -> bool:
        raise NotImplementedError('Must be overwritten')

    def get_url(self, path: str = None):
        if path is not None:
            return self.host + path
        else:
            return self.host + self.path


class Chapter(LightNovelPage):
    translator = ''
    previous_chapter_path = ''
    next_chapter_path = ''
    content: Tag = None


class ChapterEntry:
    title = ''
    path = ''


class Book:
    title = ''
    chapters: List[ChapterEntry] = []


class Novel(LightNovelPage):
    translator = ''
    description: Tag = None
    books: List[Book] = []
    first_chapter_path = ''
    img_url = ''


class LightNovelApi(LightNovelEntity, ABC):
    proxy: proxyutil.Proxy = None

    def __init__(self, proxy: proxyutil.Proxy = proxyutil.DirectProxy):
        """
        Creates a new API for a specific service.
        :param proxy: The proxy to use when executing http requests.
        """
        super().__init__()
        self.proxy = proxy

    def _get_document(self, url: str) -> BeautifulSoup:
        """
        Downloads an html document from a given url.
        :param url: The url where the document is located at.
        :return: An instance of BeautifulSoup which represents the html document.
        """
        with self.proxy.request('GET', url) as response:  # Not actually needed, but something something Consistency
            response.raise_for_status()
            return BeautifulSoup(response.text, features="html5lib")

    def get_novel(self, url: str) -> Novel:
        """
        Downloads the main page of the novel from the given url.
        :param url: The url where the page is located at.
        :return: An instance of a Novel.
        """
        return Novel(self._get_document(url))

    def get_chapter(self, url: str) -> Chapter:
        """
        Downloads a chapter from the given url.
        :param url: The url where the chapter is located at.
        :return: An instance of a Chapter.
        """
        return Chapter(self._get_document(url))

    def get_entire_novel(self, url: str, delay=1.0) -> Tuple[Novel, List[Chapter]]:
        """
        Downloads the main page of a novel and then all its chapters.
        This method dow not only try to get the chapters from the chapter list
        on the main page, but also follows the links to the next chapter if they
        are available on the current chapter.

        If the main page did not get parsed properly, the function returns the parsed novel
        and an empty list.
        :param url: The url where the main page of the novel is located at.
        :param delay: The time duration in seconds for which to wait between downloads.
        :return: A tuple with an instance of the Novel and a list of the downloaded chapters.
        """
        novel = self.get_novel(url)
        if not novel.parse():
            self.log.warning("Couldn't parse novel page. No chapters will be extracted.")
            return novel, []
        chapters = []
        chapter = None
        for book in novel.books:
            for chapter_entry in book.chapters:
                chapter = self.get_chapter(self.get_url(chapter_entry.path))
                if not chapter.parse():
                    self.log.warning("Failed parsing chapter.")
                time.sleep(delay)
                chapters.append(chapter)
        while chapter.success and chapter.next_chapter_path:
            self.log.debug(f"Following existing next chapter link({chapter.next_chapter_path}).")
            chapter = self.get_chapter(self.get_url(chapter.next_chapter_path))
            if not chapter.parse():
                self.log.warning("Failed verifying chapter.")
                break
            time.sleep(delay)
            chapters.append(chapter)
        return novel, chapters

    # TODO: Get rid of this atrocity and use a proper architecture to deal with this instead.
    def compile_to_latex_pdf(self, novel: Novel, chapters: List[Chapter], folder: str):
        from util import LatexHtmlSink
        if os.path.isdir(folder):
            shutil.rmtree(folder)
        novel_title = textutil.slugify(novel.title)
        path = os.path.join(folder, novel_title)
        if os.path.isdir(path):
            shutil.rmtree(path)
        os.makedirs(folder)
        os.makedirs(path)
        index = 0
        chapter_filenames_noext = []
        converter = LatexHtmlSink()
        for chapter in chapters:
            index += 1
            chapter_title = textutil.slugify(chapter.title)
            chapter_filename_noext = f"{index}_{chapter_title}"
            chapter_path = os.path.join(path, chapter_filename_noext + '.tex')
            chapter_filenames_noext.append(chapter_filename_noext)
            with open(chapter_path, 'w') as f:
                f.write(f"\\chapter{{{chapter.title}}}\n{converter.parse(chapter.content)}")
        with open(os.path.join(folder, novel_title, novel_title + '.tex'), 'w') as f:
            f.write(f"""\\documentclass[oneside,11pt]{{memoir}}
\\usepackage[normalem]{{ulem}}
\\usepackage{{fontspec}}
\\input{{structure.tex}}
\\title{{{novel.title}}}
\\author{{{novel.translator}}}
\\newcommand{{\\edition}}{{}}
\\makeatletter\\@addtoreset{{chapter}}{{part}}\makeatother%
\\begin{{document}}
\\thispagestyle{{empty}}
%\\ThisCenterWallPaper{{1.12}}{{cover.jpg}}
\\begin{{tikzpicture}}[remember picture,overlay]
\\node [rectangle, rounded corners, fill=white, opacity=0.75, anchor=south west, minimum width=4cm, minimum height=3cm] (box) at (-0.5,-10) (box){{}};
\\node[anchor=west, color01, xshift=-2cm, yshift=-0.8cm, text width=3.9cm, font=\\sffamily\\bfseries\\scshape\\Large] at (box.north){{\\thetitle}};
\\node[anchor=west, color01, xshift=-2cm, yshift=-1.8cm, text width=3.9cm, font=\\sffamily\\scriptsize] at (box.north){{\\edition}};
\\node[anchor=west, color01, xshift=-2cm, yshift=-2.5cm, text width=3.9cm, font=\\sffamily\\bfseries] at (box.north){{\\theauthor}};
\\end{{tikzpicture}}
\\newpage

\\tableofcontents

\\chapter*{{Synopsis}}
{converter.parse(novel.description)}
\\newpage
"""
                    )
            for chapter_title in chapter_filenames_noext:
                f.write(f"\\include{{{chapter_title}}}\n")
            f.write("\\end{document}")
        shutil.copyfile('structure.tex', os.path.join(folder, novel_title, 'structure.tex'))

    @staticmethod
    def get_api(url: str, proxy: proxyutil.Proxy = proxyutil.DirectProxy()) -> 'LightNovelApi':
        """
        Probes all available api wrappers and returns the first one that matches with the url.
        :param url: The url to be checked for.
        :param proxy: The proxy to use for the LightNovelApi.
        :return: An instance of a LightNovelApi.
        """
        from wuxiaworld import WuxiaWorldApi
        apis = [
            WuxiaWorldApi(proxy)
        ]
        parsed = parse_url(url)
        for api in apis:
            label = parse_url(api.host)
            if parsed.host == label.host:
                return api
        raise LookupError(f"No api found for url {url}.")
