import html
import re
import unicodedata


def slugify(value, allow_unicode=False, lowercase=True):
    """
    Convert to ASCII if 'allow_unicode' is False. Convert spaces to hyphens.
    Remove characters that aren't alphanumerics, underscores, or hyphens.
    Convert to lowercase. Also strip leading and trailing whitespace.
    """
    value = str(value)
    if allow_unicode:
        # noinspection SpellCheckingInspection
        value = unicodedata.normalize('NFKC', value)
    else:
        # noinspection SpellCheckingInspection
        value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = re.sub(r'[^\w\s-]', '', value).strip()
    value = value.lower() if lowercase else value
    return re.sub(r'[-\s]+', '-', value)


def sanitize_for_html(string: str) -> str:
    """
    Prepares a string for usage in an html/xml environment.
    Escapes strings for html.
    :param string: The string to sanitize.
    :return: The sanitized string.
    """
    return html.escape(string.replace("&", "&amp;"))
