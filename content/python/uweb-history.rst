Reflection and introspection: µWeb in review
############################################

:date: 2014-05-07
:tags: Python, µWeb, not-invented-here
:status: published

.. class:: post-intro

    This is the first part of a series that looks back on previous projects. There is a lot to learn from looking critically at ourselves, both admitting mistakes and acknowledging achievements. The first project will be µWeb, and will likely take up more than one installment. The foundations for this were laid in 2009, and that's where the story starts.

During my time at Google, even working on the operations (hardware) side, there was a good bit of software involved. We made small scripts and applications that made everyday life go better and smoother. The tool of the trade was Python, and I quickly developed a strong liking for it. My fondness for it turned out to be infectious and my partner in programming developed a similar preference. To be fair, coming from a PHP_ background, what was there *not* to like...

Where it all began
==================

In early 2009, we had started to become fond of pylint for analysis of our codebase. Static analysis in a dynamic language like Python isn't perfect. In fact, it's very far from it, but it still makes life easier, and a useful tool. It will point out a fair amount of type mismatches (sometimes ones that aren't), unreachable code, unused or missing arguments, name- and style errors.

We liked it enough in fact, that a script was written to run pylint on our entire codebase in a comprehensive manner. The script would run periodically, checking out each of the new revisions and linting all the (Python) source files that were changed in each revision. The messages and final score would be stored in a database, providing a look at code quality over the course of development of the code.

Of course, storing data is no good if you're not going to *do* something with it, so we set out to make something that allowed us to visualize the growth and maturing of our code. We decided it should be a web application if anything, the rationale being that developing a proper GUI would be a lot more work. The follow-up question to that of course is: what would we build it on top of?

Enter mod_python
================

Some time not long before we had a brief encounter with Django_, for a volunteer project for Bits of Freedom. It had felt like a lot of setting up and configuring and a good bit of working against the grain. Most likely this was due to a lack of experience, bad assumptions or the fact that everyone was using a different version of a project seeing rapid development. Nevertheless, we weren't going to go with Django for this. We didn't go with any existing framework in fact; we figured that our project was simple enough that we could build it right on top of a web server, or as close as you can reasonably get (did I mention that PHP background and the terrible habits it inspired?).

We were accustomed to Apache, so we explored the different ways in which we could get Apache to serve a Python web project. There are `a few ways to go about this`__, in summary and in no particular order:

__ `Python webservers`_

* CGI -- spawns a process for each request, making it dreadfully slow
* fastCGI -- long-running processes that Apache interacts with
* mod_wsgi_ -- Apache module for Python's highly interoperable web server interface definition
* mod_python_ -- Python interpreter embedded in the Apache process

We ended up writing a few simple \``Hello World'' test applications and getting a feel for the complexity and relative performance of the various options. CGI and fastCGI were both out immediately for reasons of performance and being thoroughly unpleasant to work with. The real choice was between ``mod_wsgi`` and ``mod_python``. At the time the WSGI specification didn't mean much, and the documentation for ``mod_python`` provided significantly more handholds. We chose to base our application-to-be on ``mod_python``. The documentation gave us a quick start and in the simple comparisons we ran, performance seemed to favor it.

In hindsight, this decision was a significant misstep, though it seemed well reasoned at the time. Building an application on top of the 'wrong' platform is unfortunate; but building a framework on top of the wrong foundation brings a whole host of problems. Two obvious ones are that µWeb will only run on top of Apache, and is unable to leverage `modern lightweight and fast WSGI daemons`__. Another is that all sorts of WSGI middleware is unavailable, forcing reimplementation or recreation of many existing tools and features.

__ `WSGI webservers`_

Steadily growing complexity
===========================

The first version of our pylint-result-viewer was drafted in mid-March 2009. One of the things it contained was a home-built template parser. It would load a file from disk and replace placeholders in the file from a provided dictionary. The syntax was comparable to that of a format-string, but with a different placeholder syntax and without the options to define the formats for numbers.

By early April the :py:`handler()` function (the entry point for ``mod_python``) for this application had grown to an unmanageable 280+ lines of code. This *single-function application* consisted of a extended and nested tree of conditionals that described each path and action of the application.

One way to express the complexity of a function is by counting the number of different paths that can be taken through branches. This metric is known as the `cyclomatic complexity`_. There's a Python tool that implements a checker for this and other complexity metrics: radon_. Using this, the measured cyclomatic complexity of the :py:`handler()` function at that time point was *forty-six*.

This complexity made the function very difficult to reason about and to grow the program in an effective manner. Aside from that, it made it almost impossible to test exhaustively. Both were strong indicators that this code should be refactored, and more than a little ironic for an application that tries to highlight bad coding style. We didn't tackle it at that time though; the application provided us with the desired output and we left it at that.

The first µWeb
==============

For most of a year, the pylint-result-viewer project was left untouched and other simple web projects were created in a similar bare-bones fashion. In March of 2010, things moved forward again and the ``uweb`` module made its first appearance in our software repository.

This module provided a dispatch function much like the current µWeb URL dispatcher. The ``mod_python`` :py:`handler()` function defined a list of 2-tuples with path patterns and methods to call. These were presented together with the request and the ``PageMaker`` class on which the methods would be called.

The mentioned ``PageMaker`` is the progenitor of the current-day :py:`class uweb.PageMaker`, though only in name. At the time, it was not actually part of the ``uweb`` module, but recreated in each application that used the route dispatching provided by µWeb. Over the following months, the codebase for µWeb was slowly grown and refactored, moving more of the functionality we needed for multiple projects into the core of the module.

Development history of the template parser
==========================================

The initial version of what has become µWeb's template parser was created sometime before March 2009. At this stage it would load a template file from disk, read the contents into a string and iteratively replace template tags with the intended content. We had a few reasons to create our own template parser:

#. `Django templates`_ and Jinja_ (the other template engines we had looked at) had a significant number of dependencies and perceived code bloat. We wanted something more minimal in code size;
#. Writing our own code would create a product more tailored to our needs;
#. We would be very familiar with the functioning and options of the final product.

One way to summarize this would be to say that we created our own templating system because we would rather do that than learn to use another system. While not entirely accurate, it does describe the overly confident approach that we took.

Without a clear design goal, other than some vague ideas of the future, features were added on an ad-hoc basis. One of the first improvements, by April of 2009, was to separate loading of templates from the templating function and to keep loaded templates in memory. Some time later, support for the indexing of lists and dictionaries was added.

Development slowed for almost a year and was picked up again in December 2010. These changes were done just before the tracked history of the `µWeb repository`_ starts, while this was still very much an experimental piece of code. The main change was the way in which a template was processed.

Originally, it was an iterative string-replace system where each of the provided texts replaced a tag, and then the resulting text was used for the next tag. This meant that if the tag content matched upcoming tags, there would be recursive replacement, in addition to poor performance because of the way Python's immutable string type works. This was resolved by adding a separate parsing step to the processing of a template where the tags and the text parts between the tags were separated. This both made single-level replacements guaranteed, and improved performance significantly if the template was used more than once in the lifetime of the parser instance.

In the same development sprint, functions were added to the parser. This allowed for transformations to the inserted text other than basic HTML-escaping. This was then expanded to allow repeated calls to functions. There was no API for adding custom functions yet, though it was possible to add them to the module-global dictionary of template functions and use them that way.

Modern µWeb in review
=====================

Following this review of what happened before the release and the tracked history, the next installment will provide an analysis of the stronger and weaker aspects of µWeb as it exists today.

..  _Cyclomatic complexity: http://en.wikipedia.org/wiki/Cyclomatic_complexity
..  _Django: https://www.djangoproject.com/
..  _Django templates: https://docs.djangoproject.com/en/dev/ref/templates/
..  _Jinja: http://jinja.pocoo.org/
..  _mod_python: http://modpython.org/
..  _mod_wsgi: https://code.google.com/p/modwsgi/
..  _PHP: http://phpsadness.com
..  _Python webservers: https://docs.python.org/2.7/howto/webservers.html
..  _radon: https://pypi.python.org/pypi/radon
..  _µWeb repository: https://github.com/edelooff/newWeb/
..  _WSGI webservers: http://nichol.as/benchmark-of-python-web-servers
