import re
from lightnovel import LogBase
from bs4 import Tag, NavigableString
from typing import List


class HtmlSink(LogBase):

    def parse(self, html: Tag) -> str:
        strings = []
        for child in html.children:
            if type(child) == NavigableString:
                strings.append(self.parse_navigable_string(child))
            elif type(child) == Tag:
                strings.append(self.parse_child_tag(child))
            else:
                raise Exception("Unknown object type: {}".format(type(child)))
        return self.join_strings(strings)

    def join_strings(self, strings: List[str]) -> str:
        return str.join('\n', strings).strip()

    def parse_child_tag(self, tag: Tag) -> str:
        if tag.name == 'p':
            return self.parse_paragraph(tag)
        elif tag.name == 'hr':
            return self.parse_horizontal_rule(tag)
        else:
            raise Exception("Unknown child tag name: {}".format(tag.name))

    def parse_navigable_string(self, string: NavigableString) -> str:
        return string.__str__()

    def parse_paragraph(self, tag: Tag) -> str:
        return self.parse_sub_tag(tag)

    def parse_sub_tag(self, tag: Tag) -> str:
        string = ''
        for subtag in tag.children:
            if type(subtag) == NavigableString:
                subtag: NavigableString
                string += self.parse_navigable_string(subtag)
            elif type(subtag) == Tag:
                subtag: Tag
                if subtag.name in ['em', 'i']:
                    string += self.parse_italics(subtag)
                elif subtag.name in ['strong', 'b']:
                    string += self.parse_strong(subtag)
                else:
                    raise Exception("Unknown tag type: {}".format(subtag.name))
            else:
                raise Exception("Unknown object type: {}".format(type(subtag)))
        return string

    def parse_horizontal_rule(self, tag: Tag) -> str:
        raise NotImplementedError('Must be overwritten.')

    def parse_strong(self, tag: Tag) -> str:
        raise NotImplementedError('Must be overwritten.')

    def parse_italics(self, tag: Tag) -> str:
        raise NotImplementedError('Must be overwritten.')


class StringHtmlSink(HtmlSink):

    def parse_child_tag(self, tag: Tag) -> str:
        return tag.text.strip()


class MarkdownHtmlSink(HtmlSink):

    def join_strings(self, strings: List[str]) -> str:
        return str.join('\n\n', strings).strip()

    def parse_horizontal_rule(self, tag: Tag) -> str:
        return '---'

    def parse_italics(self, tag: Tag) -> str:
        return "_{}_".format(self.parse_sub_tag(tag))

    def parse_strong(self, tag: Tag) -> str:
        return "**{}**".format(self.parse_sub_tag(tag))


class LatexHtmlSink(HtmlSink):

    def parse_navigable_string(self, string: NavigableString) -> str:
        string = re.sub(r"[{}\\$]", '\\$1', string)
        return string

    def parse_paragraph(self, tag: Tag) -> str:
        return "{}\\\\".format(self.parse_sub_tag(tag))

    def parse_horizontal_rule(self, tag: Tag) -> str:
        return '\\hrule'

    def parse_italics(self, tag: Tag) -> str:
        return "\\textit{{{}}}".format(self.parse_sub_tag(tag))

    def parse_strong(self, tag: Tag) -> str:
        return "\\textbf{{{}}}".format(self.parse_sub_tag(tag))
