from lightnovel import LightNovelApi
from util import HtmlProxy, HtmlCachingProxy
import os
import logging

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(name)16s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=logging.DEBUG
)
logging.getLogger("urllib3").setLevel(logging.ERROR)

# Set it
URL = 'https://www.wuxiaworld.com/novel/heavenly-jewel-change'
CACHE = '.cache'
OUT = 'out'
DOWNLOAD = False

# Make it
proxy = HtmlCachingProxy(CACHE) if DOWNLOAD else HtmlProxy(CACHE)
api = LightNovelApi.get_api(URL, proxy.request)
if not proxy.load(os.path.join(CACHE, api.name, URL.split('/')[-1])):
    raise Exception("Couldn't set up proxy")

# Rip,
novel, chapters = api.get_whole_novel(URL, 1.0 if DOWNLOAD else 0.0)

# Export it
api.compile_to_latex_pdf(novel, chapters, OUT)
