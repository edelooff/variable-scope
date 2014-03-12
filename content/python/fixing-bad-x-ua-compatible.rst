Fixing bad value "X-UA-Compatible" with Pyramid
###############################################

:date: 2014/03/13 00:05
:tags: Pyramid, HTML, HTTP, Python

.. role:: python(code)
    :language: python
    :class: inline-code

.. role:: html(code)
    :language: html
    :class: inline-code

When you're making a website for the general public, you need to support the browsers of that general public. One of the things that can make that particularly difficult is the large install-base of older versions of Internet Explorer that don't run in standards mode by default. Specifically, IE8 and 9 still have a combined market share of about `30 percent <http://thenextweb.com/insider/2014/02/01/ie11-passes-ie10-market-share-firefox-slips-bit-chrome-gains-back-share/>`_.

By default these versions of Internet Explorer will run in *Quirks mode* rather than *Standards mode*. This is good for websites that were made over a decade ago and targeted IE6, but it's a disaster for modern web development because the amount of corrective CSS required is astounding. The fix is to tell them to use their *edge* rendering mode; that is, the closest they can get to actual standards. From there the path to proper behavior is manageable. Microsoft has explained how to do all of this in their `knowledge base <http://msdn.microsoft.com/en-us/library/jj676915(v=vs.85).aspx>`_, but in practice it comes down to this:

.. code-block:: html

    <meta http-equiv="X-UA-Compatible" content="IE=edge,chrome=1">

This will instruct Internet Explorer to use a Chrome Frame if available, and if not, use the latest rendering mode available (edge). With Google having `discontinued <http://blog.chromium.org/2013/06/retiring-chrome-frame.html>`_ Chrome Frame though, it's probably best to help those users to upgrade away from older Internet Explorer versions, though that's outside the scope of this article.

So what's the problem?
======================

There are a few problems with the meta tag approach, the most obvious being that it doesn't validate. It's a Microsoft specific meta tag that isn't part of the specification.

Does validation really matter? The answer depends on who you ask, and the context of the question. Obviously `some <http://github.com>`_ `don't <http://techcrunch.com>`_ `mind <http://yahoo.com>`_ the lack of validation and will use this meta tag, but if validation is reasonably attainable, you should probably aim for it.

Often enough during development of a site something will be not working how you want it. Validating your document for obvious syntactical errors is a good first step and verifying that a document has zero errors is a lot faster than weeding out your errors and warnings that \``couldn't possibly be the problem I'm having.''

Providing X-UA-Compatible as header using Pyramid
=================================================

Instead of specifying this meta tag, we can also provide an HTTP header for Internet Explorer. This way Explorer knows which mode to render in before the first byte of HTML even arrives. The header we need to set is the same :code:`X-UA-Compatible`, with similar values.

Pyramid offers an easy way to add this header to all relevant (HTML) responses. This is done by installing an `event listener <http://docs.pylonsproject.org/projects/pyramid/en/latest/narr/events.html>`_ which waits for new responses. Whenever a response is created, the new event listener runs through the following requirements check:

* If the requesting user agent is Internet Explorer;
* And the content-type of the response is a form of HTML;
* Then add the :code:`X-UA-Compatible` header to the response's header dictionary, directing IE to use edge mode.

.. code-block:: python

    from pyramid import events

    @events.subscriber(events.NewResponse)
    def add_xua_header(event):
      """Adds the X-UA-Compatible header for HTML responses to IE."""
      if ('MSIE' in (event.request.user_agent or '') and
          'html' in (event.response.content_type or '')):
        event.response.headers['X-UA-Compatible'] = 'IE=edge,chrome=1'

Both of the conditionals check against the attribute or an empty string. This is done because a client can perform a request without a :code:`user-agent` header, and in certain cases a :code:`content-type` header is not provided. Falling back to strings ensures the check fails without raising an exception for trying to iterate on :code:`None`.

Place this script with your other events, or in a file somewhere in your Pyramid project. This decorator method depends on the use of :python:`config.scan()`. More about events and how to use them can be found in the `Pyramid docs <http://docs.pylonsproject.org/projects/pyramid/en/latest/narr/events.html>`_.

Other concerns
==============

Aaron Layton of `ValidateThis <http://www.validatethis.co.uk/news/fix-bad-value-x-ua-compatible-once-and-for-all/>`_ mentions two other concerns with the meta tag solution:

* Rendering speed. Once Explorer finds this tag, rendering needs to be restarted. By supplying this information as a header, Internet Explorer knows ahead of time what mode to operate in.
* Download speed and bandwidth usage concerns. The header takes up less bytes than the meta tag and selectively serving it to only explorer reduces bandwidth consumption even further.

His first argument is a solid one. As mentioned the difference is a fraction of a second, but it's a definite benefit. The delay introduced by the rendering restart can be reduced by placing the meta tag at the top of the :html:`<head>`, just after the charset definition (though you should probably make that a header as well, for similar reasons).

The second argument I think is not very convincing. With content compression enabled, it's in fact likely that the header will consume more space. Pretty much every decent web server has gzip (or its less respected cousin *deflate*) compression enabled. In typical cases this will compress transmitted HTML (and thus the :code:`X-UA-Compatible` meta tag) to roughly 30% of the original size. The HTTP specification doesn't contain header compression, and TLS header compression is a `really bad idea <http://en.wikipedia.org/wiki/CRIME_(security_exploit)>`_, so the comparison is compressed HTML vs uncompressed header.

Uncompressed, the header solution is 35 bytes against 64 for the meta tag. Looking at the actual *bytes-over-the-wire* number, the meta tag is good for ~22 bytes against 35 bytes for the header. 50% more bandwidth by making it a header -- yes, but the difference is marginal, likely not more than 0.1% of your page size. The decision for supplying :code:`X-UA-Compatible` as either HTTP header or meta tag depends on how you want to solve the problem you're having, not on the bandwidth differences.

Postscript
==========

Irony demands that this blog theme contains the :code:`X-UA-Compatible` meta tag. There's no way to solve this on the application layer of this blog, given that the application layer is simply not there; there are only static files (see the `initial post <{filename}../meta/hello-world.rst>`_ for details). With no application code to determine whether or not to set the header, the remaining option is to set it from the HTTP daemon.

While this is certainly a feasible solution, it would mean that parts far away from the frontend code (HTML, CSS) control frontend behavior. Experience has taught me that this sort of sharding makes bugs both more likely to happen and harder to find. Configuration management would help with that, but that's another topic entirely.
