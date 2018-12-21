import setuptools
import lightnovel

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name='lightnovelapi',
    version=lightnovel.__version__,
    author='Raphael Emberger',
    description='Client sided API to light novel hosters',
    long_description=long_description,
    long_description_content_type="text/markdown",
    keywords="light-novel novel lightnovel wuxiaworld",
    license="MIT",
    url='https://github.com/raember/lightnovelapi',
    packages=setuptools.find_packages(exclude=['*test*']),
    install_requires=['beautifulsoup4'],
    test_suite="lightnovel/test",
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3.7',
        'Topic :: Internet :: WWW/HTTP :: Indexing/Search',
        'Topic :: Other/Nonlisted Topic',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ]
)
