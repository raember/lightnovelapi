import logging

from lightnovel import LightNovelApi
from pipeline import EpubMaker, Parser, DeleteChapters, HtmlCleaner
from util import Proxy

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(name)18s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=logging.INFO
)
logging.getLogger("urllib3").setLevel(logging.ERROR)

# Set it
# URL = 'https://www.wuxiaworld.com/novel/warlock-of-the-magus-world'  # TODO: Fix missing toc
# URL = 'https://www.wuxiaworld.com/novel/heavenly-jewel-change'  # TODO: Fix missing cover
# URL = 'https://www.wuxiaworld.com/novel/martial-world'
# URL = 'https://www.wuxiaworld.com/novel/sovereign-of-the-three-realms'
# URL = 'https://www.wuxiaworld.com/novel/i-shall-seal-the-heavens'
# URL = 'https://www.wuxiaworld.com/novel/stellar-transformations'
# URL = 'https://www.wuxiaworld.com/novel/a-will-eternal'
# URL = 'https://www.wuxiaworld.com/novel/battle-through-the-heavens'
# URL = 'https://www.wuxiaworld.com/novel/i-reincarnated-for-nothing'
# URL = 'https://www.wuxiaworld.com/novel/the-divine-elements'
# URL = 'https://www.wuxiaworld.com/novel/wu-dong-qian-kun'
# URL = 'https://www.wuxiaworld.com/novel/the-sword-and-the-shadow'
# URL = 'https://www.wuxiaworld.com/novel/ancient-strengthening-technique'  # TODO: Karma/VIP
# URL = 'https://www.wuxiaworld.com/novel/renegade-immortal'

for URL in [
    # 'https://www.wuxiaworld.com/novel/warlock-of-the-magus-world',
    # 'https://www.wuxiaworld.com/novel/heavenly-jewel-change',
    # 'https://www.wuxiaworld.com/novel/martial-world',
    # 'https://www.wuxiaworld.com/novel/sovereign-of-the-three-realms',
    # 'https://www.wuxiaworld.com/novel/i-shall-seal-the-heavens',
    # 'https://www.wuxiaworld.com/novel/stellar-transformations',
    # 'https://www.wuxiaworld.com/novel/a-will-eternal',
    # 'https://www.wuxiaworld.com/novel/battle-through-the-heavens',
    # 'https://www.wuxiaworld.com/novel/i-reincarnated-for-nothing',
    # 'https://www.wuxiaworld.com/novel/the-divine-elements',
    # 'https://www.wuxiaworld.com/novel/wu-dong-qian-kun',
    # 'https://www.wuxiaworld.com/novel/the-sword-and-the-shadow',
    'https://www.wuxiaworld.com/novel/ancient-strengthening-technique',
    # 'https://www.wuxiaworld.com/novel/renegade-immortal',
]:
    # Make it
    proxy = Proxy()
    api = LightNovelApi.get_api(URL, proxy)

    # Rip,
    novel, gen = api.get_entire_novel(URL)

    # Export it
    gen = Parser(api.proxy).wrap(gen)
    gen = HtmlCleaner().wrap(gen)
    # gen = ChapterConflation(novel).wrap(gen)
    gen = EpubMaker(novel).wrap(gen)
    gen = DeleteChapters().wrap(gen)
    list(gen)
    # gen.__next__()
    # gen.__next__()
    # gen.__next__()
    # gen.__next__()
    # gen.close()
