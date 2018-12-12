from setuptools import setup
import lightnovel

LONG_DESC = open('README.md').read()
VERSION = lightnovel.__version__
setup(name='LightNovelApi',
      version=VERSION,
      description='Client sided API to light novel hosters',
      long_description_content_type="text/markdown",
      long_description=LONG_DESC,
      author='raember',
      keywords="light-novel novel lightnovel wuxiaworld",
      license="MIT",
      url='https://github.com/raember/lightnovelapi',
      packages=['lightnovel'],
      package_dir={'lightnovel': 'lightnovel'},
      test_suite="lightnovel/test"
      )
