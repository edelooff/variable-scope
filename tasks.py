# Third-party modules
from invoke import task

CONFIG = {
    'deploy_dir': 'output-publish/',
    'remote_host': 'neumann',
    'remote_path': '/var/www/variable-scope.com/'}


@task
def develop(ctx):
    ctx.run('pip install -r requirements.txt')


@task
def build(ctx):
    ctx.run('pelican -s pelicanconf.py')


@task
def serve(ctx):
    print('Running preview server on http://localhost:8000')
    ctx.run('pelican -s pelicanconf.py --autoreload --listen', pty=True)


@task
def publish(ctx):
    ctx.run('pelican -s publishconf.py')
    ctx.run(
        'rsync -ahvz --delete {deploy_dir} '
        '{remote_host}:{remote_path}'.format(**CONFIG))
