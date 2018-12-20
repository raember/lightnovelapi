import json
from lightnovel import Chapter
from bs4 import BeautifulSoup, Tag, NavigableString
from urllib3.util.url import parse_url
from . import WuxiaWorld


class WuxiaWorldChapter(WuxiaWorld, Chapter):
    id = 0
    is_teaser = False
    content: Tag = None

    def _parse(self, document: BeautifulSoup):
        head = document.select_one('head')
        json_str = head.select_one('script[type=application/ld+json]').text
        json_data = json.loads(json_str)
        self.translator = json_data['author']['name']
        # self.title = head.select_one('meta[property=og:title]').get('content').replace('  ', ' ')
        url = head.select_one('meta[property=og:url]').get('content')
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
