from lightnovel import WuxiaWorldApi
from util import slugify, HtmlProxy
import os
import logging

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(name)16s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=logging.DEBUG
)


FOLDER = os.path.join('test', 'data', slugify("heavenly-jewel-change"))

# api = WuxiaWorldApi()
# novel, chapters = api.get_whole_novel('/novel/heavenly-jewel-change', 1.0)

# if os.path.isdir(FOLDER):
#     shutil.rmtree(FOLDER)
# os.mkdir(FOLDER)

# filename = novel.path.replace('/', '_') + '.html'
# with open(os.path.join(FOLDER, filename), 'w') as f:
#     f.write(novel.document.__str__())
# for chapter in chapters:
#     filename = chapter.path.replace('/', '_') + '.html'
#     with open(os.path.join(FOLDER, filename), 'w') as f:
#         f.write(chapter.document.__str__())

proxy = HtmlProxy(FOLDER)
proxy.load()
api = WuxiaWorldApi(proxy.request)
novel, chapters = api.get_whole_novel('/novel/heavenly-jewel-change', 0.0)
api.compile_to_latex_pdf(novel, chapters)

# api.compile_to_latex_pdf(novel, chapters)
