import logging

import gc

from lightnovel.util import Proxy
from lightnovel.wuxiaworld import WuxiaWorldApi

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(name)16s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=logging.DEBUG
)

api = WuxiaWorldApi(Proxy('../.cache'))
api.get_entire_novel('https://www.wuxiaworld.com/novel/warlock-of-the-magus-world')
gc.collect()
api.get_entire_novel('https://www.wuxiaworld.com/novel/heavenly-jewel-change')
gc.collect()
