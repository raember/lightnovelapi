import logging

from lightnovel import LightNovelApi
from pipeline import EpubMaker, Parser, DeleteChapters
from util import Proxy

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(name)18s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=logging.DEBUG
)
logging.getLogger("urllib3").setLevel(logging.ERROR)

# Set it
# URL = 'https://www.wuxiaworld.com/novel/warlock-of-the-magus-world'  # TODO: Fix missing toc
# URL = 'https://www.wuxiaworld.com/novel/heavenly-jewel-change'  # TODO: Fix missing cover
# URL = 'https://www.wuxiaworld.com/novel/martial-world'
# URL = 'https://www.wuxiaworld.com/novel/sovereign-of-the-three-realms'
URL = 'https://www.wuxiaworld.com/novel/i-shall-seal-the-heavens'

# Make it
proxy = Proxy()
api = LightNovelApi.get_api(URL, proxy)

# Rip,
novel, gen = api.get_entire_novel(URL)

# Export it
gen = Parser(api.proxy).wrap(gen)
# gen = HtmlCleaner().wrap(gen)
# gen = ChapterConflation(novel).wrap(gen)
gen = EpubMaker(novel).wrap(gen)
gen = DeleteChapters().wrap(gen)
list(gen)
# gen.__next__()
# gen.__next__()
# gen.__next__()
# gen.__next__()
# gen.close()
