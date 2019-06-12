import logging

from lightnovel import LightNovelApi
from pipeline import ChapterConflation
from transform import EpubTransformer
from util import Proxy

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(name)16s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=logging.DEBUG
)
logging.getLogger("urllib3").setLevel(logging.ERROR)

# def coroutine(func: Callable):
#     def start(*args, **kwargs):
#         cr = func(*args, **kwargs)
#         cr.__next__()
#         return cr
#     return start
#
#
# @coroutine
# def grep(pattern):
#     while True:
#         line = yield
#         if pattern in line:
#             print(line)
#
#
# g = grep('e')
# g.send('python')
# g.send('test')
# g.send('args')
# g.close()
# exit(0)




# Set it
# URL = 'https://www.wuxiaworld.com/novel/warlock-of-the-magus-world'
URL = 'https://www.wuxiaworld.com/novel/heavenly-jewel-change'

# Make it
api = LightNovelApi.get_api(URL, Proxy())

# Rip,
novel, gen = api.get_entire_novel(URL)
list(ChapterConflation(novel).wrap(gen))

# Export it
# api.compile_to_latex_pdf(novel, chapters, 'out')
trans = EpubTransformer(novel)
trans.export('out.epub')
