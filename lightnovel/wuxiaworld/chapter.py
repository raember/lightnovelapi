import json
from lightnovel.log_class import LogBase
from typing import List, Union
from bs4 import BeautifulSoup, Tag, NavigableString


class WuxiaWorldChapter(LogBase):
    title = ''
    translator = ''
    is_teaser = False
    previous_chapter_path = '/novel/'
    next_chapter_path = '/novel/'
    url = 'https://www.wuxiaworld.com/novel/'

    def __init__(self, bs: BeautifulSoup):
        super().__init__()
        self.log.debug('Extracting data from html.')
        head = bs.select_one('head')
        json_str = head.select_one('script[type=application/ld+json]').text
        json_data = json.loads(json_str)
        self.translator = json_data['author']['name']
        # self.title = head.select_one('meta[property=og:title]').get('content').replace('  ', ' ')
        self.url = head.select_one('meta[property=og:url]').get('content')
        for script_tag in head.select('script'):
            script = script_tag.text.strip('\n \t;')
            if script.startswith('var CHAPTER = '):
                json_str = script[14:]
                json_data = json.loads(json_str)
                self.title = json_data['name']
                self.is_teaser = json_data['isTeaser']
                self.previous_chapter_path = json_data['prevChapter']
                self.next_chapter_path = json_data['nextChapter']
                break
        if self.title == '':
            self.log.warning("Couldn't extract data from CHAPTER variable.")
        self.content = self._process_content(bs.select_one('div.p-15 div.fr-view'), self.title)

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
                if child.name == 'p':
                    if len(child.text.strip('\n ')) == 0:
                        # self.log.debug("Empty paragraph.")
                        pass
                    else:
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
                    self.log.error("Unexpected tag name: {}".format(child.name))
            else:
                self.log.error("Unexpected type: {}".format(child))
        return new_content
