import logging
from argparse import ArgumentParser, Namespace
from pathlib import Path
from typing import List

from spoofbot import Firefox, Chrome, Windows, MacOSX, Linux, OS, Browser
from spoofbot.adapter import FileCacheAdapter
from urllib3.util import parse_url, Url

import lightnovel
from lightnovel import LightNovelApi, NovelEntry
from lightnovel.pipeline import EpubMaker, Parser, DeleteChapters, StatisticsMaker
from lightnovel.qidianunderground_org import QidianUndergroundOrgApi
from lightnovel.webnovel_com import WebNovelComApi
from lightnovel.wuxiaworld_com import WuxiaWorldComApi


# https://www.wuxiaworld.com/novel/second-life-ranker
# https://www.wuxiaworld.com/novel/refining-the-mountains-and-rivers
# https://www.wuxiaworld.com/novel/otherworldly-merchant
# https://www.wuxiaworld.com/novel/phoenixs-requiem
# https://www.wuxiaworld.com/novel/duke-pendragon
# followed chapters index messed up


def get_os(arg: str) -> OS:
    if arg == 'win':
        return Windows()
    elif arg == 'mac':
        return MacOSX()
    else:
        return Linux()


def get_browser(arg: str, **kwargs) -> Browser:
    if arg == 'ff':
        return Firefox(**kwargs, ff_version=(85, 0))
    else:
        return Chrome(**kwargs)


# noinspection SpellCheckingInspection
def get_log(verbose: bool) -> logging.Logger:
    if verbose:
        logging.basicConfig(format=log_format, datefmt=date_format, level=logging.DEBUG)
        logger = logging.getLogger(__name__)
        logger.info("Set logging level to DEBUG.")
    else:
        logging.basicConfig(format=log_format, datefmt=date_format, level=logging.INFO)
        logger = logging.getLogger(__name__)
    logging.getLogger('urllib3.connectionpool').setLevel(logging.INFO)
    logging.getLogger('chardet.charsetprober').setLevel(logging.INFO)
    logging.getLogger('chardet.universaldetector').setLevel(logging.INFO)
    return logger


def search_apis(apis: List[LightNovelApi], search: str = None) -> Url:
    search_results: List[NovelEntry] = []
    for api in apis:
        if isinstance(api, WebNovelComApi):
            matches = api.search_for_specific_title(args.search)
        else:
            matches = api.search(search)
        for search_result in matches:
            log.info(f"{len(search_results)} - {search_result} ({search_result.url})")
            search_results.append(search_result)
    if len(search_results) == 0:
        log.error("Could not find any matching title.")
        exit(1)
    else:
        choice = None
        if len(search_results) == 1:
            choice = search_results[0]
        while choice is None:
            try:
                choice = search_results[int(input('Please choose the index of the url to scrape: '))]
            except KeyboardInterrupt:
                log.info("Stopping")
                exit(1)
            except Exception as e:
                log.error(f"Error while reading input: {e}")
        return choice.url


def get_args() -> Namespace:
    parser = ArgumentParser(description='Lightnovel API client.')
    # Setup
    parser.add_argument('-b', '--browser', dest='browser', action='store', metavar='NAME',
                        choices=['ff', 'chrome'], default='ff',
                        help='the browser to use (ff/chrome). Default: ff')
    parser.add_argument('-o', '--os', dest='os', action='store', metavar='OS',
                        choices=['win', 'mac', 'linux'], default='win',
                        help='the OS to use (win/mac/linux). Default: win')
    # Cache
    parser.add_argument('-c', '--cache', dest='cache', action='store', default='.cache',
                        help='the cache folder. set to empty string for no cache.')

    # Jobs
    parser.add_argument('--update', dest='update', action='store_true', default=False,
                        help='only check for updates chapters')
    parser.add_argument('--epub', dest='epub', action='store_true', default=False,
                        help='compile epub files from the books')

    # Novel set
    parser.add_argument(dest="urls", action="store", metavar='URL', nargs='*', type=parse_url, default=[],
                        help='urls of the web novels to scrape')
    parser.add_argument('--search', nargs='?', const='?',
                        help='a title to search for on available hosters. Leave empty to search interactively')
    parser.add_argument('--use-cached', dest='use_cached', action='store_true', default=False,
                        help='use cached novel urls')

    # Apis
    parser.add_argument('--wuxiaworld', dest='ww', action='store_true', default=False,
                        help='Process all hosted WuxiaWorld books')
    parser.add_argument('--qidian-underground', dest='qu', action='store_true', default=False,
                        help='Process all hosted QidianUnderground books (takes webnovel into account)')

    # Miscellaneous
    parser.add_argument('-v', '--verbose', dest='verbose', action='store_true', default=False,
                        help='be verbose')
    # noinspection SpellCheckingInspection
    parser.add_argument('--version', action='version', version=f'%(prog)s {lightnovel.__version__}')

    return parser.parse_args()


# noinspection SpellCheckingInspection
log_format = '%(asctime)s %(levelname)-8s %(name)23s: %(message)s'
date_format = '%Y-%m-%d %H:%M:%S'

if __name__ == '__main__':
    args = get_args()

    # Setup
    browser = get_browser(args.browser, os=get_os(args.os))
    log = get_log(args.verbose)

    # Cache
    use_cache = args.cache != ''
    if use_cache:
        cache = Path(args.cache)
        log.info(f"Using cache dir: {cache}")
        cache.parent.mkdir(parents=True, exist_ok=True)
        adapter = FileCacheAdapter(str(cache.absolute()))
    else:
        log.warning("Not using a cache.")
        adapter = browser.get_adapter('https://')
    browser.adapter = adapter

    # Job
    if args.update and not use_cache:
        log.error("Cannot only check for updated chapters without a cache.")
        exit(1)
    if args.epub and args.update:
        log.error("Cannot only check for updated chapters but still compile a full epub.")
        exit(1)
    if args.update:
        log.info("Job: Update novel(s)")
    elif args.epub:
        log.info("Job: Compile epub for novel(s)")
    else:
        log.info("Job: Scrape full novel(s)")

    # Novel set
    urls: List[Url] = []
    ww_api = WuxiaWorldComApi(browser)
    wn_api = WebNovelComApi(browser)
    qu_api = QidianUndergroundOrgApi(browser)
    wn_api.qidian_underground_api = qu_api
    apis = [ww_api, wn_api, qu_api]
    if args.urls:
        log.info(f"Processing {len(args.urls)} novel{'s' if len(args.urls) >= 0 else ''}")
        urls = args.urls
    # noinspection PyTypeChecker
    elif args.search is not None:
        if args.search == '?':
            args.search = input("Please enter a title to search for: ")
        urls.append(search_apis(apis, args.search))
    elif args.ww:
        log.info("Scraping entire WuxiaWorld")
        entries = []
        for entry in ww_api.search(count=200):
            if entry.url.path.startswith('/novel'):
                log.info(f"  - {entry.title}")
                entries.append(entry)
                urls.append(entry.url)
            else:
                log.debug(f"Discarding {entry}, because it's a preview novel.")
        log.info(f"Found {len(entries)} novels")
    elif args.qu:
        log.info("Scraping entire QidianUnderground")
        for entry in qu_api.search():
            urls.append(entry.url)
        log.info(f"Found {len(urls)} novels")
    elif args.use_cached:
        if not isinstance(adapter, FileCacheAdapter):
            log.error("Cannot use cached urls without a cache.")
            exit(1)
        log.info("Only processing already cached novels:")
        for api in apis:
            cached = adapter.list_cached(parse_url(api.novel_url))
            log.info(f"  {api.hoster_name}: {len(cached)} cached novels")
            urls += cached
    else:
        log.info("Nothing to do")
        exit(0)

    # Start
    input("Hit [Enter] to start: ")
    stats_maker = StatisticsMaker(browser)
    try:
        for url in urls[:]:
            # 264 - https://www.webnovel.com/book/legend-of-legends_11564749505437305
            # Json decoding problem because of odd number of backslashes
            # 700 - https://www.webnovel.com/book/world's-best-martial-artist_14495258805541605
            # json decoding problem because of multiple backslashes
            # 707 - https://www.webnovel.com/book/xianxia-my-junior-sisters-are-freaks!_19971574606292805
            # json decoding problem because of double quote
            # adapter.delete(url, {'Accept': 'text/html'})
            api = LightNovelApi.get_api(url, apis)
            novel = api.get_novel(url)
            if novel is None:
                continue
            log.info(f'Processing "{novel.title}" ({novel.url})')
            fetching_strategy = api.fetch_updated if args.update else api.fetch_all
            gen = fetching_strategy.generate_chapters(novel)

            # Export it
            gen = Parser(browser).wrap(gen)
            gen = stats_maker.wrap(gen)
            # gen = HtmlCleaner().wrap(gen)
            # gen = ChapterConflation(novel).wrap(gen)
            if args.epub:
                gen = EpubMaker(novel).wrap(gen)
            gen = DeleteChapters().wrap(gen)
            list(gen)  # Force generation
    except KeyboardInterrupt:
        log.info("Stopping")
    finally:
        stats_maker.report()
