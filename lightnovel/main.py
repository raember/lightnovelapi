import logging

from lightnovel import LightNovelApi
from pipeline import ChapterConflation, EpubMaker, Parser
from util import Proxy

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(name)16s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=logging.DEBUG
)
logging.getLogger("urllib3").setLevel(logging.ERROR)

# Set it
# URL = 'https://www.wuxiaworld.com/novel/warlock-of-the-magus-world'
# URL = 'https://www.wuxiaworld.com/novel/heavenly-jewel-change'
URL = 'https://www.wuxiaworld.com/novel/martial-world'
# URL = 'https://www.wuxiaworld.com/novel/sovereign-of-the-three-realms'

# Make it
api = LightNovelApi.get_api(URL, Proxy())

# Rip,
novel, gen = api.get_entire_novel(URL)

# Export it
gen = Parser(api.proxy).wrap(gen)
gen = ChapterConflation(novel).wrap(gen)
gen = EpubMaker(novel).wrap(gen)
# DeleteChapters().wrap(gen)
# gen.__next__()
gen.__next__()
