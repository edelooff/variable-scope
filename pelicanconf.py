#!/usr/bin/env python
# -*- coding: utf-8 -*- #
from __future__ import unicode_literals

AUTHOR = u'Elmer de Looff'
SITENAME = u'Variable Scope'
TIMEZONE = 'Europe/Amsterdam'
CC_LICENSE = 'CC-BY-SA'
CC_ATTR_MARKUP = False

DISPLAY_CATEGORIES_ON_MENU = False
DISPLAY_TAGS_ON_SIDEBAR = True
DEFAULT_PAGINATION = 4
SUMMARY_MAX_LENGTH = 300
TYPOGRIFY = True

PLUGIN_PATH = 'pelican-plugins'
PLUGINS = 'better_figures_and_images', 'related_posts', 'sitemap'

RELATED_POSTS_MAX = 4
RESPONSIVE_IMAGES = True
SITEMAP = {'format': 'xml'}

# Sidebar and social config settings
GITHUB_USER = 'edelooff'
GITHUB_SKIP_FORK = True
USE_OPEN_GRAPH = False
LINKS = ()
SOCIAL = (
    ('Google+', 'https://plus.google.com/+ElmerdeLooff'),
    ('GitHub', 'http://github.com/edelooff'),
)

# Theme and theme configuration
THEME = 'pelican-bootstrap3'
BOOTSTRAP_THEME = 'cosmo'
PYGMENTS_STYLE = 'monokai'
CUSTOM_CSS = 'static/overrides.css'

# Configure content directory and non-article content to include
PATH = 'content'
STATIC_PATHS = 'images', 'static'
EXTRA_PATH_METADATA = {
    'static/robots.txt': {'path': 'robots.txt'},
    'static/favicon.ico': {'path': 'favicon.ico'},
}
FAVICON = 'favicon.ico'

ARTICLE_URL = 'posts/{slug}'
ARTICLE_SAVE_AS = 'posts/{slug}/index.html'
PAGE_URL = 'pages/{slug}'
PAGE_SAVE_AS = 'pages/{slug}/index.html'
AUTHOR_SAVE_AS = ''

# Disable feed creation for development
FEED_ALL_ATOM = None
FEED_ALL_RSS = None
CATEGORY_FEED_ATOM = None
TRANSLATION_FEED_ATOM = None
