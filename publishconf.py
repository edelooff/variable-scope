#!/usr/bin/env python
# -*- coding: utf-8 -*- #
from __future__ import unicode_literals

# This file is only used if you use `make publish` or
# explicitly specify it as your config file.

import os
import sys
sys.path.append(os.curdir)
from pelicanconf import *

SITEURL = 'http://variable-scope.com'
RELATIVE_URLS = False

DISQUS_SITENAME = 'variablescope'
FEED_ALL_ATOM = 'feeds/all.atom.xml'
CATEGORY_FEED_ATOM = 'feeds/%s.atom.xml'

DELETE_OUTPUT_DIRECTORY = True

ARTICLE_SAVE_AS = 'posts/{slug}'
PAGE_SAVE_AS = 'pages/{slug}'
