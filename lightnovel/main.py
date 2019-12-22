import logging

from pipeline import EpubMaker, Parser, DeleteChapters
from util import Proxy
from wuxiaworld import WuxiaWorldApi

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(name)18s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=logging.INFO
)
logging.getLogger("urllib3").setLevel(logging.ERROR)
log = logging.getLogger(__name__)

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

# Make it
proxy = Proxy()
api = WuxiaWorldApi(proxy)
lst, _ = api.search2(count=200)
# print(api.login('', ''))
# print(api.get_karma())
# print(api.claim_daily_karma())
# print(api.get_karma())
# print(api.logout())
# exit(0)
# URLS = [
#     # 'https://www.wuxiaworld.com/novel/warlock-of-the-magus-world',
#     # 'https://www.wuxiaworld.com/novel/heavenly-jewel-change',
#     # 'https://www.wuxiaworld.com/novel/martial-world',
#     # 'https://www.wuxiaworld.com/novel/sovereign-of-the-three-realms',
#     # 'https://www.wuxiaworld.com/novel/i-shall-seal-the-heavens',
#     # 'https://www.wuxiaworld.com/novel/stellar-transformations',
#     # 'https://www.wuxiaworld.com/novel/a-will-eternal',
#     # 'https://www.wuxiaworld.com/novel/battle-through-the-heavens',
#     # 'https://www.wuxiaworld.com/novel/i-reincarnated-for-nothing',
#     # 'https://www.wuxiaworld.com/novel/the-divine-elements',
#     # 'https://www.wuxiaworld.com/novel/wu-dong-qian-kun',
#     # 'https://www.wuxiaworld.com/novel/the-sword-and-the-shadow',
#     # 'https://www.wuxiaworld.com/novel/ancient-strengthening-technique',
#     # 'https://www.wuxiaworld.com/novel/renegade-immortal',
#     # 'https://www.wuxiaworld.com/novel/perfect-world'
#     'https://www.wuxiaworld.com/novel/the-unrivaled-tang-sect'
# ]
newly_fetched = {}
urls = list(map(lambda i: i.get_url(), lst))
for url in urls:
    # Rip,
    novel, gen = api.get_entire_novel(url)
    if not novel.success:
        log.error("Failed getting novel")
        continue
    newly_fetched[novel.title] = 0

    # Export it
    gen = Parser(api.proxy).wrap(gen)
    # gen = HtmlCleaner().wrap(gen)
    # gen = ChapterConflation(novel).wrap(gen)
    gen = EpubMaker(novel).wrap(gen)
    gen = DeleteChapters().wrap(gen)
    for _ in gen:
        if not proxy.hit:
            newly_fetched[novel.title] += 1

print("New chapters:")
for title, amount in newly_fetched.items():
    print(f"{amount} new chapters in {title}")
