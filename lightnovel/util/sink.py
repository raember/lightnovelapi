import re
from bs4 import Tag, NavigableString
from typing import List


class HtmlSink:

    def parse(self, html: Tag) -> str:
        strings = []
        for child in html.children:
            if type(child) == NavigableString:
                strings.append(self._parse_navigable_string(child))
            elif type(child) == Tag:
                strings.append(self._parse_child_tag(child))
            else:
                raise Exception("Unknown object type: {}".format(type(child)))
        return self._join_strings(strings)

    def _join_strings(self, strings: List[str]) -> str:
        return str.join('\n', strings).strip()

    def _parse_child_tag(self, tag: Tag) -> str:
        if tag.name in ['p', 'div', 'a']:
            return self._parse_paragraph(tag)
        elif tag.name == 'blockquote':
            print(tag.contents)
            return self._parse_paragraph(tag.contents[0])
        elif tag.name == 'hr':
            return self._parse_horizontal_rule(tag)
        else:
            raise Exception("Unknown child tag name: {}".format(tag.name))

    def _parse_navigable_string(self, string: NavigableString) -> str:
        return string.__str__()

    def _parse_paragraph(self, tag: Tag) -> str:
        return self._parse_sub_tag(tag)

    def _parse_sub_tag(self, tag: Tag) -> str:
        string = ''
        for subtag in tag.children:
            if type(subtag) == NavigableString:
                subtag: NavigableString
                string += self._parse_navigable_string(subtag)
            elif type(subtag) == Tag:
                subtag: Tag
                if subtag.name in ['em', 'i']:
                    string += self._parse_italics(subtag)
                elif subtag.name in ['strong', 'b']:
                    string += self._parse_strong(subtag)
                elif subtag.name in ['a', 'span', 'sup']:
                    string += self._parse_link(subtag)
                elif subtag.name in ['p']:
                    string += self._parse_paragraph(tag.contents[0])
                elif subtag.name in ['br', 'img']:
                    pass
                else:
                    raise Exception("Unknown tag type: {}({})".format(subtag.name, subtag))
            else:
                raise Exception("Unknown object type: {}".format(type(subtag)))
        return string

    def _parse_horizontal_rule(self, tag: Tag) -> str:
        raise NotImplementedError('Must be overwritten.')

    def _parse_strong(self, tag: Tag) -> str:
        raise NotImplementedError('Must be overwritten.')

    def _parse_italics(self, tag: Tag) -> str:
        raise NotImplementedError('Must be overwritten.')

    def _parse_link(self, tag: Tag) -> str:
        return self._parse_sub_tag(tag)


class StringHtmlSink(HtmlSink):

    def _parse_child_tag(self, tag: Tag) -> str:
        return tag.text.strip()


class MarkdownHtmlSink(HtmlSink):

    def _join_strings(self, strings: List[str]) -> str:
        return str.join('\n\n', strings).strip()

    def _parse_horizontal_rule(self, tag: Tag) -> str:
        return '---'

    def _parse_italics(self, tag: Tag) -> str:
        return "_{}_".format(self._parse_sub_tag(tag))

    def _parse_strong(self, tag: Tag) -> str:
        return "**{}**".format(self._parse_sub_tag(tag))


class LatexHtmlSink(HtmlSink):

    def _parse_navigable_string(self, string: NavigableString) -> str:
        string = string.strip('\n\t ')
        string = re.sub(r"–", '–', string)
        string = re.sub(r"([&%$#_{}])", r'\\\1', string)
        string = re.sub(r"…(…(\.|)|)", '...', string)
        string = re.sub(r"\b\.\.\.\b", '...', string)
        string = re.sub(r"~", '\\textasciitilde', string)
        string = re.sub(r"\^", '\\textasciicircum', string)
        string = re.sub(r"\.\.\.\.+", '...', string)
        string = re.sub(r"(?<=[^!?\"]) (?=[,.!?])", '', string)
        return string

    def _parse_paragraph(self, tag: Tag) -> str:
        return "{}\\\\ \\relax".format(self._parse_sub_tag(tag))

    def _parse_horizontal_rule(self, tag: Tag) -> str:
        return '\\hrule'

    def _parse_italics(self, tag: Tag) -> str:
        return "\\textit{{{}}}".format(self._parse_sub_tag(tag))

    def _parse_strong(self, tag: Tag) -> str:
        return "\\textbf{{{}}}".format(self._parse_sub_tag(tag))
