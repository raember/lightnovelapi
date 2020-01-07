import logging

from spoofbot import Firefox
from spoofbot.adapter import CacheAdapter

from pipeline import EpubMaker, Parser, DeleteChapters
from wuxiaworld_com import WuxiaWorldComApi

# from settings import EMAIL, PASSWORD

# noinspection SpellCheckingInspection
logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(name)18s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=logging.INFO
)
logging.getLogger("urllib3").setLevel(logging.ERROR)
# noinspection SpellCheckingInspection
logging.getLogger('chardet.charsetprober').setLevel(logging.ERROR)
log = logging.getLogger(__name__)

# Set it
browser = Firefox()
browser._accept_encoding = ['deflate', 'gzip']  # brotli (br) is cumbersome
cache = CacheAdapter()
browser.session.mount('https://', cache)
browser.session.mount('http://', cache)

# Make it
api = WuxiaWorldComApi(browser)

# print(f"Login successful: {api.login(EMAIL, PASSWORD)}")
# karma_normal, karma_golden = api.get_karma()
# print(f"Karma: {karma_normal} normal, {karma_golden} golden")
# print(f"Claiming karma successful: {api.claim_daily_karma()}")  # Idk why it doesn't claim them. It doesn't work. Maybe better like this tbh
# karma_normal, karma_golden = api.get_karma()
# print(f"Karma: {karma_normal} normal, {karma_golden} golden")
# print(f"Logout successful: {api.logout()}")

lst = api.search(count=200)
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
urls = list(map(lambda i: i.url, lst[16:]))
for url in urls:
    # Rip,
    novel, gen = api.get_entire_novel(url)
    if not novel.success:
        log.error("Failed getting novel")
        continue
    newly_fetched[novel.title] = 0

    # Export it
    gen = Parser(api.browser).wrap(gen)
    # gen = HtmlCleaner().wrap(gen)
    # gen = ChapterConflation(novel).wrap(gen)
    gen = EpubMaker(novel).wrap(gen)
    gen = DeleteChapters().wrap(gen)
    for _ in gen:
        if not cache.hit:
            newly_fetched[novel.title] += 1

print("New chapters:")
for title, amount in newly_fetched.items():
    print(f"{amount} new chapters in {title}")
