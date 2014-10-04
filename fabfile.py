# Standard modules
import os
import subprocess
import sys
import SimpleHTTPServer
import SocketServer
import threading

# Third-party modules
from fabric.api import env, hide, local, task
from fabric.contrib import project

# Fabric configuration for the local deployment path and target hosts
env.deploy_path = 'output/'
env.remote_path = '/var/www/blog'
env.hosts = 'neon',


@task
def install_deps():
  local('sudo apt-get install libxft-dev zlib1g-dev libjpeg-dev')
  local('pip install pillow beautifulsoup4 rst2pdf')


@task
def build():
  local('pelican -ds pelicanconf.py')


@task
def preview():
  local('pelican -ds publishconf.py')


@task
def regenerate():
  local('pelican -drs pelicanconf.py')


@task
def reserve():
  """Hack to spin up a continuous content generator and also serve locally."""
  def fab_regenerate():
    subprocess.Popen(['fab', 'regenerate']).communicate()

  def fab_serve():
    subprocess.Popen(['fab', 'serve']).communicate()

  threads = [
      threading.Thread(target=fab_regenerate),
      threading.Thread(target=fab_serve)]
  [thread.start() for thread in threads]
  [thread.join() for thread in threads]


@task
def serve():
  class AddressReuseTCPServer(SocketServer.TCPServer):
    allow_reuse_address = True

  os.chdir(env.deploy_path)
  host, port = '0.0.0.0', 8000
  server = AddressReuseTCPServer(
      (host, port), SimpleHTTPServer.SimpleHTTPRequestHandler)

  sys.stderr.write('Serving on http://{0}:{1} ...\n'.format(host, port))
  server.serve_forever()


@task
def publish():
  with hide('output'):
    preview()
    project.rsync_project(
        remote_dir=env.remote_path,
        local_dir=env.deploy_path,
        delete=True)
