from .api import LightNovelApi, Novel, Book, ChapterEntry, Chapter, request
from .wuxiaworld import WuxiaWorldApi
import logging

logging.basicConfig(
        format='%(asctime)s %(levelname)-8s %(name)16s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        level=logging.DEBUG
)

__version__ = "0.1"
