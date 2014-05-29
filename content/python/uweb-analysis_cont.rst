Reflection and introspection: an analysis of µWeb (continued)
#############################################################

:date: 2014/05/31
:tags: Python, µWeb, not-invented-here
:status: draft

Pagemaker
=========

The part where most of the actual application will happen is the presenter layer of µWeb. This is largely represented by the :py:`class PageMaker`, or typically subclass in µWeb projects. When the routes for a project are defined, each route gets assigned a handler method, which will be looked up on the class which is assigned to the router's ``PAGE_CLASS``. [#page_class]_

When the application has been set up and requests are handled, the request dispatcher will go through the defined routes until it finds a match, and immediately delegate the request to the method specified on the route. This is also the first shortcoming of the PageMaker and request router system.


Handling method purely selected based on route match
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

While route matching itself works fine for many frameworks, the direct coupling of a route to a handling method leaves for very little flexibility. There is no built-in functionality to discriminate and delegate requests based on

* request method (GET, POST, PUT etc);
* match-values from the route regex;
* accept headers (for content negotiation), or any other headers;
* whether or not the request is an XmlHTTPRequest.

This lack of pre-selection means that the selection must happen explicitly in the handler code, where it must then choose to delegate this to separate methods for separate content, or combine all the possible responses in one large method body. In addition, handlers that should only respond to a very narrow selection must actively raise errors, rather than allow the framework to handle the situation where no match for the route exists:

.. code-block:: python
    :linenos: table

    class Application(uweb.PageMaker):
        def article(self, article_id_from_route):
            if self.req.method == 'POST':
                return self._article_update(article_id_from_route)
            elif self.req.method == 'GET':
                return self._article_view(article_id_from_route)
            # return "404 Not Found" or "405 Method Not Allowed"
            # Alternatively treat all non-POST as if it were GET

        def _article_update(self, article_id):
            # check if user is logged in and may edit
            # check form; update article or return warnings

        def _article_view(self, article_id):
            # return article

Pyramid_ solves this with the ``view_config`` decorator which you can attach to your request handlers. To use these with url dispatching, you add routes by defining a route regex and assigning it a name. The ``view_config`` decorator uses this ``route_name`` and any predicates (i.e. true/false test) to select the requests that are handled by the decorated function or class.

.. code-block:: python
    :linenos: table

    @view_config(route_name='article', request_method='GET')
    def view_article(request):
        # return article

    @view_config(route_name='article', request_method='POST', permission='edit')
    def update_article(request):
        # check form, update article or return warnings

As hinted at above, the ``view_config`` also allows testing of user permissions, removing the need to check permission levels in your actual request handling code (where you really don't want to handle that sort of thing). Pyramid's authentication and authorization systems are outside the scope of this post, but there's an excellent tutorial with examples available. [#pyramid_auth_demo]_


No way to assign a renderer to a request handler
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The design for µWeb is such that request handler methods must return the string which contains the full response, or return a ``Response_`` object. This means that request methods must load and parse their templates explicitly and return the result, instead of returning a dictionary of keys to be used by the renderer mechanism in creating the response.

This latter mechanism allows for easier testing (because testing a dictionary response is far easier than parsing the resultant template), keeps the request handler code cleaner, and if support exists in the framework, allows the same handler body to fulfill multiple kinds of requests.

.. pyramid example for XHR-negotiated Mako, JSON response


Next heading
~~~~~~~~~~~~~

Not convenient to split handling methods over several files: causes complex subclassing that needs to be handled at runtime


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

The PID of the server process is not communicated, nor is its location. The storage location based on the package name and the router name, and cannot be defined by the user. The storage location is :code:`/var/lock/underdark/{package}/{router}.pid`. The indirect way in which the ``uweb`` script starts a web project makes it impossible to track with a system like Upstart_, and probably other similar task managers. See the `Upstart appendix`__ for a solution on how to manage µWeb projects with it.

__ `Appendix A: Making standalone play nice with Upstart`_


Appendix A: Making standalone play nice with Upstart
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When you're trying to make µWeb's standalone server play nice with Ubuntu's Upstart, you're going to run into some problems. Upstart supports managing (double-forking) daemons, but starting a project with the ``uweb`` script triggers 4 forks: [#strace]_

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

..  [#page_class] setting up a router's ``PAGE_CLASS`` is described in the documentation: http://uweb-framework.nl/docs/Request_Router
..  [#pyramid_auth_demo] Pyramid Auth Demo: http://michael.merickel.org/projects/pyramid_auth_demo/
..  [#tail] http://www.computerhope.com/unix/utail.htm
..  [#strace] Measured using ``strace`` on :code:`uweb start logviewer` as explained here: http://upstart.ubuntu.com/cookbook/#how-to-establish-fork-count.
..  [#expect] :code:`expect` allows Upstart to keep track of the correct process ID. http://upstart.ubuntu.com/cookbook/#expect

..  _pyramid: http://www.pylonsproject.org/projects/pyramid/about
..  _response: http://uweb-framework.nl/docs/Response
..  _upstart: http://upstart.ubuntu.com/cookbook/
