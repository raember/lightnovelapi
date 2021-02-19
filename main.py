import logging
from argparse import ArgumentParser
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


# noinspection SpellCheckingInspection
log_format = '%(asctime)s %(levelname)-8s %(name)23s: %(message)s'
date_format = '%Y-%m-%d %H:%M:%S'

if __name__ == '__main__':
    parser = ArgumentParser(description='Lightnovel API client.')
    parser.add_argument(dest="urls", action="store", metavar='URL', nargs='*', type=parse_url, default=[],
                        help='urls of the web novels to scrape')
    parser.add_argument('-b', '--browser', dest='browser', action='store', metavar='NAME',
                        choices=['ff', 'chrome'], default='ff',
                        help='the browser to use (ff/chrome). Default: ff')
    parser.add_argument('-o', '--os', dest='os', action='store', metavar='OS',
                        choices=['win', 'mac', 'linux'], default='win',
                        help='the OS to use (win/mac/linux). Default: win')
    parser.add_argument('-c', '--cache', dest='cache', action='store', default='.cache',
                        help='the cache folder. set to empty string for no cache.')
    parser.add_argument('--search', nargs='?', const='?',
                        help='a title to search for on available hosters')
    parser.add_argument('--use-cached', dest='use_cached', action='store_true', default=False,
                        help='use cached novel urls')
    parser.add_argument('--update', dest='update', action='store_true', default=False,
                        help='only check for updates chapters')
    parser.add_argument('--epub', dest='epub', action='store_true', default=False,
                        help='compile epub files from the books')
    parser.add_argument('--wuxiaworld', dest='ww', action='store_true', default=False,
                        help='Iterate through all hosted WuxiaWorld books')
    parser.add_argument('--qidian-underground', dest='qu', action='store_true', default=False,
                        help='Iterate through all hosted QidianUnderground books (takes webnovel into account)')
    parser.add_argument('-v', '--verbose', dest='verbose', action='store_true', default=False,
                        help='be verbose')
    # noinspection SpellCheckingInspection
    parser.add_argument('--version', action='version', version=f'%(prog)s {lightnovel.__version__}')
    args = parser.parse_args()

    log = get_log(args.verbose)
    browser = get_browser(args.browser, os=get_os(args.os))
    adapter = FileCacheAdapter(args.cache)
    if args.cache != '':
        browser.adapter = adapter
    else:
        log.warning("Not using a cache.")
        adapter = browser.get_adapter('https://')

    if args.update and args.cache == '':
        log.error("Cannot only check for updated chapters without a cache.")
        exit(1)
    if args.epub and args.update:
        log.error("Cannot only check for updated chapters but still compile a full epub.")
        exit(1)

    urls: List[Url] = args.urls
    # noinspection PyTypeChecker
    ww_api = WuxiaWorldComApi(browser)
    wn_api = WebNovelComApi(browser)
    qu_api = QidianUndergroundOrgApi(browser)
    wn_api.qidian_underground_api = qu_api
    apis = [ww_api, wn_api]
    if args.search is not None:
        if args.search == '?':
            args.search = input("Please enter a title to search for: ")
        search_results: List[NovelEntry] = []
        for api in [ww_api, wn_api]:
            if isinstance(api, WebNovelComApi):
                matches = api.search_for_specific_title(args.search)
            else:
                matches = api.search(args.search)
            for search_result in matches:
                log.info(f"{len(search_results)} - {search_result} ({search_result.url})")
                search_results.append(search_result)
        if len(search_results) == 0:
            log.error("Could not find any matching title.")
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
            urls.append(choice.url)

    missed_novels = []

    if args.ww:
        for entry in ww_api.search(count=100):
            if entry.url.path.startswith('/novel'):
                urls.append(entry.url)
            else:
                log.debug(f"Discarding {entry}, because it's a preview novel.")

    if args.qu:
        for entry in qu_api.search():
            matches = wn_api.search_for_specific_title(entry.title)
            if len(matches) == 0:
                log.error(f"Could not find any matching title on webnovel for {entry}.")
                missed_novels.append(entry)
            else:
                first_match = matches[0]
                if len(matches) > 1:
                    log.info(f"Chose {first_match} out of: {', '.join(map(str, matches))}")
                urls.append(first_match.url)
        log.info(f"Found {len(urls)}/{len(urls) + len(missed_novels)} novels ({len(missed_novels)} missed)")

    if args.use_cached:
        if not isinstance(adapter, FileCacheAdapter):
            log.error("Cannot use cached urls without a cache.")
            exit(1)
        for api in [ww_api, wn_api]:
            cached = adapter.list_cached(api.novel_url)
            log.info(f"{api.hoster}: {len(cached)} cached novels")
            urls += cached

    if len(urls) == 0 or not args.epub and not args.update:
        log.info("Nothing to do")
        exit(0)

    stats_maker = StatisticsMaker(browser)
    try:
        for url in urls:
            api = LightNovelApi.get_api(url, apis)
            novel = api.get_novel(url)
            if novel is None:
                continue
            log.info(f"Processing {novel}")
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
