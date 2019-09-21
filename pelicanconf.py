AUTHOR = 'Elmer de Looff'
SITENAME = 'Variable Scope'
TIMEZONE = 'Europe/Amsterdam'
CC_LICENSE = 'CC-BY-SA'
CC_ATTR_MARKUP = False
DEFAULT_DATE = 'fs'
DISPLAY_CATEGORIES_ON_MENU = False
DISPLAY_TAGS_ON_SIDEBAR = True
DEFAULT_PAGINATION = 4
SUMMARY_MAX_LENGTH = 300
TYPOGRIFY = True

PLUGIN_PATHS = ['custom-plugins', 'pelican-plugins']
PLUGINS = [
    'better_figures_and_images',
    'extra_rst_roles',
    'i18n_subsites',
    'related_posts',
    'summary']

RELATED_POSTS_MAX = 4
RESPONSIVE_IMAGES = True

# Sidebar and social config settings
GITHUB_USER = 'edelooff'
GITHUB_SKIP_FORK = True
USE_OPEN_GRAPH = False
LINKS = ()
SOCIAL = [('GitHub', 'http://github.com/edelooff')]

# Theme and theme configuration
THEME = 'pelican-themes/pelican-bootstrap3'
BOOTSTRAP_THEME = 'cosmo'
JINJA_ENVIRONMENT = {'extensions': ['jinja2.ext.i18n']}
PYGMENTS_STYLE = 'github'
CUSTOM_CSS = 'static/overrides.css'

# Configure content directory and non-article content to include
PATH = 'content'
STATIC_PATHS = 'images', 'static'
EXTRA_PATH_METADATA = {
    'static/robots.txt': {'path': 'robots.txt'},
    'static/favicon.ico': {'path': 'favicon.ico'},
}
FAVICON = 'favicon.ico'

AUTHOR_URL = 'author/{slug}.html'
AUTHOR_SAVE_AS = 'author/{slug}/index.html'
ARTICLE_URL = 'posts/{slug}'
ARTICLE_SAVE_AS = 'posts/{slug}/index.html'
PAGE_URL = 'pages/{slug}'
PAGE_SAVE_AS = 'pages/{slug}/index.html'

# Disable feed creation for development
FEED_ALL_ATOM = None
FEED_ALL_RSS = None
CATEGORY_FEED_ATOM = None
TRANSLATION_FEED_ATOM = None
