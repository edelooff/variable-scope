Reflection and introspection: an analysis of µWeb (continued)
#############################################################

:date: 2014/06/08
:tags: Python, µWeb, not-invented-here


Presentation layer / Pagemaker
==============================

The part where most of the actual application work will happen is in the presentation layer of µWeb, also referred to as the ``PageMaker``. This is largely represented by the :py:`class PageMaker`, or typically subclass in µWeb projects. When the routes for a project are defined, each route gets assigned a handler method, which will be looked up on the class which is assigned to the router's ``PAGE_CLASS``. [#page_class]_

When the application has been set up and requests are handled, the request dispatcher will go through the defined routes until it finds a match, and immediately delegate the request to the method specified on the route. This is also the first shortcoming of the PageMaker and request router system.


Request handler selected only by route match
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

While route matching itself works fine for many frameworks, the direct coupling of a route to a handling method leaves very little flexibility in the system. There is no built-in functionality to discriminate and delegate requests based on

* request method (GET, POST, PUT etc);
* match-values from the route regex;
* content type of the request body;
* ``accept`` headers (for content negotiation);
* whether or not the request is an XMLHttpRequest.


Delegating based on request-method in µWeb
------------------------------------------

This lack of pre-selection means that the selection must happen explicitly in the handler code, where it must then choose to delegate this to separate methods for separate content, or combine all the possible responses in one large method body. In addition, handlers that should only respond to a very narrow selection must actively raise errors, rather than allow the framework to handle the situation where no match for the route exists:

.. code-block:: python
    :linenos: inline

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


Request-method predicates in Pyramid
------------------------------------

Pyramid_ solves this with the ``view_config`` decorator which you can attach to your request handlers. To use these with url dispatching, you add routes by defining a route regex and assigning it a name. The ``view_config`` decorator uses this ``route_name`` and any predicates (i.e. true/false test) to select the requests that are handled by the decorated function or class.

.. code-block:: python
    :linenos: table

    @view_config(route_name='article', request_method='GET')
    def view_article(request):
        # return article

    @view_config(route_name='article', request_method='POST', permission='edit')
    def update_article(request):
        # check form, update article or return warnings

As hinted at above, the ``view_config`` also allows testing of user permissions, removing the need to check permission levels in your actual request handling code (where you really don't want to handle that sort of thing). Pyramid's authentication and authorization systems are outside the scope of this post, but there's excellent documentation and an example project available. [#pyramid_auth_docs]_ [#pyramid_auth_demo]_


No way to assign a renderer to a request handler
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The design for µWeb is such that request handler methods must return the string which contains the full response, or return a `Response object`__. There is no framework-provided means of attaching a template renderer (or any other renderer) to a handler. This means that request methods must load and parse their templates explicitly and return the result, instead of returning a dictionary of keys to be used by the renderer mechanism in creating the response.

__ `uweb response object`_

Separating the rendering of the template from the creation of the template input also enforces a clean separation between presentation and preparation. It keeps the code clean and allows for easier testing of what goes into the template, because it only requires validating a dictionary instead of parsing the constructed template.


Attaching a template renderer in Bottle
---------------------------------------

Bottle_ implements this by using the ``@view`` decorator to attach a template to a request handler. Multiple routes can be handled by the same request (requiring multiple ``@route`` decorators), and all use the same template to return output:

.. code-block:: python

    @route('/hello')
    @route('/hello/<name>')
    @view('hello_template')
    def hello(name='World'):
        return dict(name=name)


Per-view renderer in Pyramid
----------------------------

Pyramid allows for something even more flexible, where the renderer is assigned in the ``@view_config`` decorator. This allows for the same request handler to have different renderers based on view predicates. This allows for content negotiation in APIs, for example by allowing the user to select :abbr:`JSON (JavaScript Object Notation)` or :abbr:`XML (eXtensible Markup Language)` response bodies by sending the relevant ``accept`` header. In the example below, we use it to return either a full-page response to regular requests, or a partial-content response for :abbr:`XHR (XMLHttpRequest)`-requests:

.. code-block:: python

    @view_config(route_name='search', renderer='full-page-result.mak')
    @view_config(route_name='search', renderer='partial-items.mak', xhr=True)
    def view_search(request):
        return perform_search(request.params.get('q'))

In this example, the :code:`full-page-result.mak` template returns a full page with header, footer and all other static parts. The results are added into this page by including the :code:`partial-items.mak` template and using it to process the results. This way, the template can be reused for the AJAX-call to retrieve only the next page of search results without requiring any duplication.


Renderer switching in µWeb
--------------------------

Content negotiation isn't very common for regular clients (because browsers are terrible with accept headers), but differentiating between XHR and 'normal' requests is. Let's take the above example for Pyramid and create the closest thing we can in µWeb. Because there's no view or renderer configuration, this decision making needs to be done in the request handler. Recreating the previous example in µWeb's PageMaker leads to something similar to this:

.. code-block:: python

    class PageMaker(uweb.PageMaker):
        def view_search(self):
            # There's combined 'params' attribute, so read the query param
            results = perform_search(self.req.get.get('q'))
            if self.req.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return self.parser.Parse('partial-result.html', **results)
            return self.parser.Parse('full-page-results.html', **results)


Static content handler limitations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

µWeb comes included with a handler for static content, which does a fairly good job of fulfilling the usual needs of static content serving. However, the way it's implemented has some downsides, because of the initial design assumption that every project needs one and only one static content handler.

The static content directory defaults to :code:`static`, relative to the module that contains the project's PageMaker. If this needs to be changed, the class variable :code:`PUBLIC_DIR` should be set to the desired directory.

While no second static directory can be served, multiple static paths *are* possible. The following route definitions lead to three subdirectories of the static directory:

.. code-block:: python

    ROUTES = [
        ('/(robots.txt)', 'Static'),
        ('/(images/.*)', 'Static'),
        ('/(javascript/.*)', 'Static'),
        ('/(stylesheets/.*)', 'Static'),
    ]

These route definitions will serve files from the following directory tree::

    static/
        robots.txt
        images/
            ceilingcat.jpg
            longcat.jpg
        javascript/
            jquery-1.11.1.min.js
            application-0.2-min.js
        stylesheets/
            normalize.min.css
            application-0.1.min.css

What the sole static content handler will not allow you to do is serve content from two different root directories. If you have a situation like that, you'll have to write your own static content handler (or adapt the one included in the source).


All handlers are forced into one class
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

As we established previously, µWeb's request handlers are weighed down by code preparing template variables because of limitations in the template parser. A design decision in the presenter aspect of µWeb forces all request handlers to be part of the same class. These two limitations combined mean that non-trivial projects quickly reach a point where the ``PageMaker`` class exceeds a thousand lines of code. This doesn't cause problems in and of itself, but it makes it more difficult to create a good mental map of the class.

"Can't you separate things?" Well, yes you can. You can create a series of separate classes, grouped by their function within the project, and store each in their separate module. You have your *main* :py:`class PageMaker` inherit from all of those classes *and* the µWeb main ``PageMaker`` and you're on your way to success.

The downside of this is that many (eventually) sibling methods will be defined in another class, and that care needs to be taken to not accidentally define two methods of the same name. Accessing methods defined in another class (or in the framework's provided ``PageMaker``) will cause warnings in analytical tools and context-aware code completion will fail to work nicely.


Database layer / ORM
====================

For straightforward databases in simple applications, the model does a fairly good job of providing an interface to your database without getting in your way. It leaves the definition of the database schema up to the developer and requires no information about it (nor is any retrieved at runtime). This means there's no requirement to define the field types, foreign keys and other constraints in the code for the various mechanisms to work. This makes it very easy to get started with the µWeb ORM.

Unfortunately, most databases are not straightforward, nor are real-world applications *simple* by any stretch of the imagination. There are a lot of shortcomings to the model when comparing it to any of the popular ORMs such as SQLAlchemy_, but even for a limited-functionality starting point, there are some very painful limitations.


Bad transactional support
~~~~~~~~~~~~~~~~~~~~~~~~~

If there is any one reason to not use the provided database model module, it's because of its transaction management. There is transaction support, and transactions are used, but the scope of them is just plain wrong.

For a web application, the scope of the transaction is usually the handling of the request. During the lifetime of this request, the application will read from one or more tables, update some rows, and insert across multiple tables when adding an object. If *any* of the operations fail, we typically want *none* of them persisted because it leaves the system in a bad state. Pseudocode for this interaction might look a bit like this:

.. code-block:: python

    with transaction_factory as session:
        # Transaction begins
        bob = session.query(User, {'name': 'bob'})
        session.insert(Charge, {'user': bob, 'amount': 29.50})
        session.insert(Charge, {'user': bob, 'amount': -10})
        session.update(Balance, {'user': bob, 'amount': 19.50})
        # Transaction commits

In this scenario, should the balance updating fail because of a key constraint, or in the case that something else in the handling of the request goes wrong, the whole of the transaction will be left uncommitted. Either all actions succeed, or nothing will have happened.

In the µWeb ORM, the transactional scoping is effectively the following:

.. code-block:: python

    with transaction_factory as session:
        bob = session.query(User, {'name': 'bob'})
    with transaction_factory as session:
        session.insert(Charge, {'user': bob, 'amount': 29.50})
    with transaction_factory as session:
        session.insert(Charge, {'user': bob, 'amount': -10})
    with transaction_factory as session:
        session.update(Balance, {'user': bob, 'amount': 19.50})

What happens is that each change to the system is made permanent, regardless of any errors that might happen later on. This means that if for some reason the balance update fails (or any other error happens), the two charges are still stored, leaving the database in an inconsistent state.

This means that every request handler that changes or adds data in two separate actions is a potential point of data corruption.


Relationship loading replaces the foreign key value
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

One of the things that makes the µWeb ORM easy to get going with is the automatic loading of (assumed) relationships. That is, for a set of tables like the following::

    -- TABLE `message`
    +----+--------+--------------------------------------------------+
    | ID | author | message                                          |
    +----+--------+--------------------------------------------------+
    |  1 |      1 | First message!                                   |
    |  2 |      2 | Robert'); DROP TABLE Students;--                 |
    |  3 |      1 | You didn't think it would be this easy, did you? |
    +----+--------+--------------------------------------------------+

    -- TABLE `author`
    +----+-------+-------------------+
    | ID | name  | emailAddress      |
    +----+-------+-------------------+
    |  1 | John  | john@example.com  |
    |  2 | Bobby | bobby@tables.com  |
    +----+-------+-------------------+

And a model definition like this:

.. code-block:: python

    from uweb import model
    class Author(model.Record):
      """Abstraction class for author records."""

    class Message(model.Record):
      """Abstraction class for messages records."""

Accessing the :py:`'author'` key on a loaded :py:`message` object will automatically query the database for the relevant :py:`author` object and replace the numeric value with it, before returning the author object. This is great if you need to know something about the author, like their name or email address. But if you only needed the key value, it gets in the way *and* it costs a query.


Record.GetRaw method
--------------------

While it's possible to disable automatic loading of related records altogether (on a per-table and per-column basis), there is no way to use a portion of the time. That is, have it not perform the act automatically, but upon request.

Instead of that, there is a mechanism to read the column value without triggering the automatic relationship loading. This requires the developer to use the ``GetRaw`` method of the relevant record. When accessing an item this way, automated loading is suppressed and the current value assigned to the key is returned.

However, if the related object is already loaded, this is returned instead. This means that the return type of ``GetRaw`` is not predictable, requiring all code calling it to check the type and use it appropriately.


A better way to deal with relationships
---------------------------------------

The implicit relationship management that µWeb ORM employs is hard to predict, which makes it difficult to work with. Explicit relationship management such as in SQLAlchemy [#sqla_relationships]_ requires a bit more work, but delivers consistent results. There, an attribute is defined which will load the related objects when accessed. This is done using the defined or detected Foreign Key relationship to that table.

While relationships are not detected in µWeb ORM, explicit configuration is possible and should have been implemented. This would remove the potential side-effects of item access and prevent the replacement of data, leading to all sorts of surprises.


Standalone server
=================

The standalone server included with µWeb serves two goals:

#. Running your application without requiring Apache's ``mod_python``;
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

The ``stdout`` and ``stderr`` log files by default do not contain the output of the ``logging`` module. µWeb redirects these to its own SQLite database (stored in the same location), which is not simply viewable by tailing. An application to browse and filter these databases comes bundled with µWeb, providing much-needed access to the logs. Running :code:`uweb start logviewer` starts a daemon that listens on http://localhost:8001/, which serves the log viewer.

The lack of plaintext logging means that the developer has to actively refresh the page of the log viewer (there is no automatic updating system for it). It also means that quick debugging with :code:`print` statements is less effective because the log database and ``stdout`` file need to be correlated. And while a log statement is not that much more to write, it does take the speed out of debugging, making the lack of an interactive debugger that much more apparent.


Lack of automatic reload
~~~~~~~~~~~~~~~~~~~~~~~~

The µWeb standalone server lacks an automatic reloading mechanism. This means that whenever code has changed, the server needs to be manually restarted. Most modern frameworks come with a command line option that allows for automatic reloading.

Template files are automatically reloaded when they have been changed, though this is a feature of the template system, not the standalone server.


Daemonization makes management difficult
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The PID of the server process is not communicated, nor is its location. The storage location based on the package name and the router name, and cannot be defined by the user. The storage location is :code:`/var/lock/underdark/{package}/{router}.pid`. The indirect way in which the ``uweb`` script starts a web project makes it impossible to track with a system like Upstart_, and probably other similar task managers. See the `Upstart appendix`__ for a solution on how to manage µWeb projects with it.

__ `Appendix A: Making standalone play nice with Upstart`_


In conclusion
=============

Despite the many points of criticism of µWeb in this post and the previous, I do not regret the development of it. For me personally, the creation of µWeb has been an interesting and instructive experience. It has taught me a number of valuable skills and exposed me to many new aspects of software design and development. Some of that by doing the right thing, some of that by doing the wrong thing and (eventually) recognizing that.

However, that does not mean that µWeb is a framework you, or anyone, should be using to make serious applications. There are too many flaws, large and small, that make development needlessly difficult and complex. Our original goal at Underdark of building something that was progressive and modern, that was straightforward and easy to use, has not been reached in the slightest. The current released version of µWeb is technically functional, but not in any way fit for production use.

So whereto from here? As mentioned before, for my professional use I'm more than happy with Pyramid_. If you're looking for a full-stack framework that comes with everything and the kitchen sink included (and an active community), Django_ is the project to check out.

While the former are immensely powerful, they assume strong working knowledge of Python and as such might not be the best for people new to Python. That group should probably have a look at Bottle_ or Flask_, which provide simple and clean interfaces to work with, and are well documented to boot.


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

..  [#page_class] Setting up a router's ``PAGE_CLASS`` is described in the documentation: http://uweb-framework.nl/docs/Request_Router
..  [#pyramid_auth_docs] Pyramid security documentation: http://docs.pylonsproject.org/docs/pyramid/en/latest/narr/security.html
..  [#pyramid_auth_demo] Pyramid Auth Demo: http://michael.merickel.org/projects/pyramid_auth_demo/
..  [#sqla_relationships] SQLAlchemy relationship configuration documentation: http://docs.sqlalchemy.org/en/rel_0_9/orm/relationships.html
..  [#tail] ``tail`` is a UNIX tool to output the last part of files. It optionally prints new additions to them as they are written.
..  [#strace] Measured using ``strace`` on :code:`uweb start logviewer` as explained here: http://upstart.ubuntu.com/cookbook/#how-to-establish-fork-count.
..  [#expect] The :code:`expect` stanza instructs Upstart how many forks are to be expected, allowing it to keep track of the correct process ID: http://upstart.ubuntu.com/cookbook/#expect

..  _bottle: http://bottlepy.org/
..  _django: https://www.djangoproject.com/
..  _flask: http://flask.pocoo.org/
..  _pyramid: http://www.pylonsproject.org/projects/pyramid/about
..  _sqlalchemy: http://www.sqlalchemy.org/
..  _upstart: http://upstart.ubuntu.com/cookbook/
..  _uweb response object: http://uweb-framework.nl/docs/Response
