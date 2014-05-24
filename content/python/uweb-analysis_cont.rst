Reflection and introspection: an analysis of µWeb (continued)
#############################################################

:date: 2014/05/31 01:29
:tags: Python, µWeb, not-invented-here
:status: draft

Pagemaker
=========

#. Page methods only predicated by a path -- no request_method, XHR or other predicates
#. Not convenient to split handling methods over several files: causes complex subclassing that needs to be handled at runtime
#. No way to assign a renderer for the return value of a pagemaker method (template, string, json)


Database layer / ORM
====================

Mostly very basic, but intended to be such. However, there are a few failings on this that make the model unnecessarily difficult and dangerous to use:

#. Commits transaction per table operation, no nested transactions. Causes inconsistency when 2nd operation failure cannot roll back 1st.
#. Relationship loading replaces key value but not if suppressed, need to check every time
#. Record.GetRaw suppresses relationship loading but will still return a Record instance is relationship loading already happened


Standalone server
=================

The standalone server included with µWeb serves two goals:

#. Running your application without requiring Apache's mod_python;
#. Provide a debugging server during development.

However, due to the exact design of the server it doesn't succeed well at either. At the heart of this is the daemon interface provided by the server. Starting a µWeb project without Apache present causes it to fork off a standalone server process that runs in the background. This process then redirects its ``stdout`` and ``stderr`` to a pair of log files.


Lack of output visibility
~~~~~~~~~~~~~~~~~~~~~~~~~

Because the standalone server redirects its output to two log files, there is no easily digested output on the console from where the application is run. To get the desired output you'll have to find the output files for the daemon and ``tail`` [#tail]_ them. The daemon outputs are stored in one of two locations (in order of preference):

- :code:`/var/log/underdark/{package}/`
- :code:`~/.underdark/{package}/logs/`

Another pain due to this forking nature is that the output of the startup progress is reported to the redirected output file. This means that on the terminal you started it from, there is zero feedback on whether the project started successfully or not. Nor does it tell you the port the project is served on.


Lack of plaintext logging
~~~~~~~~~~~~~~~~~~~~~~~~~

The ``stdout`` and ``stderr`` log files by default do not contain the output of the ``logging`` module. µWeb redirects these to its own SQLite database (stored in the same location), which is not simple viewable by tailing. An application to browse and filter these databases comes bundled with µWeb, providing much-needed access to the logs. Running :code:`uweb start logviewer` starts a daemon that listens on http://localhost:8001/, which serves the log viewer.

The lack of plaintext logging means that the developer has to actively refresh the page of the log viewer (there is no automatic updating system for it). It also means that quick debugging with :code:`print` statements is less effective because the log database and ``stdout`` file need to be correlated. And while a log statement is not that much more to write, it does take the speed out of debugging, making the lacking an interactive debugger that much more apparent.


Lack of automatic reload
~~~~~~~~~~~~~~~~~~~~~~~~

The µWeb standalone server lacks an automatic reloading mechanism. This means that whenever code has changed, the server needs to be manually restarted. Most modern frameworks come with a command line option that allows for automatic reloading.

Template files are automatically reloaded when they have been changed, though this is a feature of the template system, not the standalone server.


Daemonization makes management difficult
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The PID of the server process is not communicated, nor is its location. The storage location based on the package name and the router name, and cannot be defined by the user. The storage location is :code:`/var/lock/underdark/{package}/{router}.pid`.


Making standalone play nice with Upstart
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When you're trying to make µWeb's standalone server play nice with Ubuntu's Upstart_, you're going to run into some problems. Upstart supports managing (double-forking) daemons, but starting a project with the ``uweb`` script triggers 4 forks: [#strace]_

- 1: Python interpreter for the ``uweb`` script (coming from the shell)
- 2: A subprocess call to load the project's router module and start it
- 3 & 4: Double fork to daemonize the standalone process

Upstart expects [#expect]_ only up to two forks to happen, so it won't track the resulting process. This means that starting a project this way will cause it to start (successfully), while Upstart believes it failed to start. This makes stopping or restarting it using Upstart impossible.

To make the standalone server work well with Upstart, the server starting usually performed by the ``uweb`` script must be placed in hte job configuration script. Assuming we want to start the µWeb logviewer from a virtualenv installed in :code:`/usr/local/newweb/env`, the script looks like this:

.. code-block:: sh

    description "uweb-logviewer"

    manual
    respawn
    console log
    env PYTHON="/usr/local/newweb/env/bin/python"
    env ROUTER="uweb.logviewer.router.logging"
    expect daemon

    exec $PYTHON -m $ROUTER start



Footnotes & References
======================

..  [#tail] http://www.computerhope.com/unix/utail.htm
..  [#strace] Measured using ``strace`` on :code:`uweb start logviewer` as explained here: http://upstart.ubuntu.com/cookbook/#how-to-establish-fork-count.
..  [#expect] :code:`expect` allows Upstart to keep track of the correct process ID. http://upstart.ubuntu.com/cookbook/#expect

..  _upstart: http://upstart.ubuntu.com/cookbook/