import logging

from lightnovel import LightNovelApi
from transform import EpubTransformer
from util import Proxy

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(name)16s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=logging.DEBUG
)
logging.getLogger("urllib3").setLevel(logging.ERROR)

# Set it
# URL = 'https://www.wuxiaworld.com/novel/warlock-of-the-magus-world'
URL = 'https://www.wuxiaworld.com/novel/heavenly-jewel-change'

# Make it
proxy = Proxy()
api = LightNovelApi.get_api(URL, proxy)
# if not proxy.load(os.path.join(CACHE, api.name, URL.split('/')[-1])):
#     raise Exception("Couldn't set up proxy")

# Rip,
novel = api.get_entire_novel(URL)

# Export it
# api.compile_to_latex_pdf(novel, chapters, 'out')
trans = EpubTransformer(novel)
trans.conflate_chapters()
trans.export('out.epub')
