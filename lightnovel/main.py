import logging

from lightnovel import LightNovelApi
from pipeline import ChapterConflation, EpubMaker, Parser, HtmlCleaner, DeleteChapters, WaitForProxyDelay
from util import Proxy

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(name)18s: %(message)s',
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
proxy = Proxy()
api = LightNovelApi.get_api(URL, proxy)

# Rip,
novel, gen = api.get_entire_novel(URL)

# Export it
gen = Parser(api.proxy).wrap(gen)
gen = HtmlCleaner().wrap(gen)
gen = ChapterConflation(novel).wrap(gen)
gen = EpubMaker(novel).wrap(gen)
gen = DeleteChapters().wrap(gen)
gen = WaitForProxyDelay(proxy).wrap(gen)
list(gen)
# gen.__next__()
# gen.__next__()
# gen.__next__()
# gen.__next__()
# gen.close()
