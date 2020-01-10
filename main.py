import logging

from spoofbot import Firefox
from spoofbot.adapter import CacheAdapter
from urllib3.util import parse_url

from pipeline import EpubMaker, Parser, DeleteChapters
from webnovel_com import WebNovelComApi

# from settings import EMAIL, PASSWORD

# noinspection SpellCheckingInspection

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(name)23s: %(message)s',
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
# api = WuxiaWorldComApi(browser)
# lst = api.search(count=200)
# urls = list(map(lambda i: i.url, lst))

api = WebNovelComApi(browser)
lst = [
    'https://www.webnovel.com/book/7853880705001905',  # Pursuit-of-the-Truth
    'https://www.webnovel.com/book/8527113906000305',  # Reincarnation-Of-The-Strongest-Sword-God
    'https://www.webnovel.com/book/6831850602000905',  # Library-of-Heaven's-Path
    # 'https://www.webnovel.com/book/12820870105509205',  # Supreme-Magus - no qidian underground records
    'https://www.webnovel.com/book/7931338406001705',  # Release-That-Witch
    'https://www.webnovel.com/book/6838665602003405',  # Gourmet-of-Another-World
    'https://www.webnovel.com/book/11022733006234505',  # Lord-of-the-Mysteries
    'https://www.webnovel.com/book/9017100806001205',  # King-of-Gods
    # 'https://www.webnovel.com/book/13493723505001305',  # King-of-Sports - no qidian underground records
    # From https://www.webnovel.com/category/list?categoryId=70009&categoryType=1&gender=1&orderBy=1&bookType=null&bookStatus=null
    'https://www.webnovel.com/book/7834199305001505',  # Ancient-Godly-Monarch
    'https://www.webnovel.com/book/6838665602002905',  # Otherworldly-Evil-Monarch
    'https://www.webnovel.com/book/7141993106000405',  # War-Sovereign-Soaring-The-Heavens
    'https://www.webnovel.com/book/10700626806140405',  # Monster-Pet-Evolution
    'https://www.webnovel.com/book/11793789806524505',  # Dual-Cultivation
    'https://www.webnovel.com/book/9795116706003105',  # The-Legend-of-Futian
    'https://www.webnovel.com/book/14187175405584205',  # Birth-of-the-Demonic-Sword
    'https://www.webnovel.com/book/9240153405002605',  # Unrivaled-Medicine-God
    'https://www.webnovel.com/book/7996858406002505',  # Reverend-Insanity
    'https://www.webnovel.com/book/7817013305001305',  # The-Strongest-System
    'https://www.webnovel.com/book/13071505405554605',  # Legend-of-the-Mythological-Genes
    'https://www.webnovel.com/book/7834185605001405',  # True-Martial-World
    'https://www.webnovel.com/book/8411219605000605',  # Lord-Xue-Ying
    'https://www.webnovel.com/book/10385100206025505',  # Spirit-Cultivation
    'https://www.webnovel.com/book/11418908406358805',  # Black-Tech-Internet-Cafe-System
    'https://www.webnovel.com/book/8093958205004005',  # The-Legend-of-the-Dragon-King
    'https://www.webnovel.com/book/8102217006003305',  # Ultimate-Scheming-System
    'https://www.webnovel.com/book/9087079805001905',  # Legend-of-Swordsman
    'https://www.webnovel.com/book/7213811205000505',  # Swallowed-Star
    'https://www.webnovel.com/book/8335460805000105',  # Monster-Paradise
    'https://www.webnovel.com/book/7997491806002805',  # Alchemy-Emperor-of-the-Divine-Dao
    'https://www.webnovel.com/book/8324025906000205',  # God-Emperor
    'https://www.webnovel.com/book/7996858406002505',  # Reverend-Insanity
    'https://www.webnovel.com/book/10961533705222305',  # A-World-Worth-Protecting
]
urls = list(map(parse_url, lst))

# print(f"Login successful: {api.login(EMAIL, PASSWORD)}")
# karma_normal, karma_golden = api.get_karma()
# print(f"Karma: {karma_normal} normal, {karma_golden} golden")
# print(f"Claiming karma successful: {api.claim_daily_karma()}")  # Idk why it doesn't claim them. It doesn't work. Maybe better like this tbh
# karma_normal, karma_golden = api.get_karma()
# print(f"Karma: {karma_normal} normal, {karma_golden} golden")
# print(f"Logout successful: {api.logout()}")

newly_fetched = {}
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
