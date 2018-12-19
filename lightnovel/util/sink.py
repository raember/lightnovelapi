from ..log_class import LogBase
from bs4 import Tag, NavigableString
from typing import List


class HtmlSink(LogBase):

    def parse(self, html: Tag) -> str:
        strings = []
        for child in html.children:
            string = self._parse(child)
            if string is not None:
                strings.append(string)
            else:
                self.log.warning("Returned string empty. ({})".format(child))
        return self._join(strings)

    def _join(self, strings: List[str]) -> str:
        return str.join('\n', strings).strip()

    def _parse(self, el) -> str:
        if type(el) == NavigableString:
            el: NavigableString
            return el.__str__()
        elif not type(el) == Tag:
            self.log.error("Unknown object type: {}".format(type(el)))
            return None
        return self._parse_tag(el)

    def _parse_tag(self, tag: Tag) -> str:
        raise NotImplementedError('Must be overwritten.')


class StringHtmlSink(HtmlSink):

    def _parse_tag(self, tag: Tag) -> str:
        return tag.text.strip()


class MarkdownHtmlSink(HtmlSink):

    def _join(self, strings: List[str]) -> str:
        return str.join('\n\n', strings).strip()

    def _parse_tag(self, tag: Tag) -> str:
        string = ''
        if tag.name == 'p':
            for child in tag.children:
                string += self._parse(child)
            return string
        elif tag.name == 'em':
            for child in tag.children:
                string += self._parse(child)
            return "*{}*".format(string)
        elif tag.name == 'hr':
            return '---'
        else:
            self.log.warning("Unhandled tag encountered: {}".format(tag))
            return tag.__str__()


class LatexHtmlSink(HtmlSink):

    def _parse_tag(self, tag: Tag) -> str:
        string = ''
        if tag.name == 'p':
            for child in tag.children:
                string += self._parse(child)
            return "{}\\\\".format(string)
        elif tag.name == 'em':
            for child in tag.children:
                string += self._parse(child)
            return "\\textbf{" + string + '}'
        elif tag.name == 'hr':
            return '\\hrule'
        else:
            self.log.warning("Unhandled tag encountered: {}".format(tag))
            return tag.__str__()
