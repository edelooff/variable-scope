# This file is only used if you use `make publish` or
# explicitly specify it as your config file.

import os
import sys
sys.path.append(os.curdir)
from pelicanconf import *

DEFAULT_METADATA = {
    'status': 'draft',
}

SITEURL = 'http://variable-scope.com'
RELATIVE_URLS = False

PLUGINS.append('sitemap')
SITEMAP = {'format': 'xml'}

DISQUS_SITENAME = 'variablescope'
FEED_ALL_ATOM = 'feeds/all.atom.xml'
CATEGORY_FEED_ATOM = 'feeds/{slug}.atom.xml'

DELETE_OUTPUT_DIRECTORY = True
OUTPUT_PATH = 'output-publish/'

AUTHOR_SAVE_AS = 'author/{slug}'
ARTICLE_SAVE_AS = 'posts/{slug}'
PAGE_SAVE_AS = 'pages/{slug}'
