import html
import re
import unicodedata


def slugify(string: str, allow_unicode: bool = False) -> str:
    """
    Slugify a given string.

    :param string: The string to slugify.
    :param allow_unicode: Whether to allow unicode characters or only ASCII characters.
    :return: The slug.
    """
    string = str(string)
    if allow_unicode:
        # noinspection SpellCheckingInspection
        string = unicodedata.normalize('NFKC', string)
    else:
        # noinspection SpellCheckingInspection
        string = unicodedata.normalize('NFKD', string).encode('ascii', 'ignore').decode('ascii')
    string = re.sub(r'[^\w\s-]', '', string).strip()
    return re.sub(r'[-\s]+', '-', string)


def sanitize_for_html(string: str) -> str:
    """
    Prepares a string for usage in an html/xml environment. Escapes strings for html.

    :param string: The string to sanitize.
    :return: The sanitized string.
    """
    return html.escape(string.replace("&", "&amp;"))


def unescape_string(string: str) -> str:
    """
    Unescapes a string

    :param string: The string to unescape.
    :return: The unescaped string.
    """
    return string.replace(u'\xa0', ' ').encode('utf8').decode('unicode-escape').replace(r'\'', '')  # .replace(r"\'", "'").replace('\"', '"')


def normalize_string(string: str) -> str:
    """
    Normalizes strings by substituting certain unicode characters with ascii variants.

    :param string: The string to normalize.
    :return: The normalized string.
    """
    subs = {
        u'\xa0': ' ',
        '？': '?',
        '：': ':',
        '’´`': "'",
        '—': '-',
    }
    for char, sub in subs.items():
        string = string.replace(char, sub)
    return string
