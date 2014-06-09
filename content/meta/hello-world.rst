Hello world
###########

:date: 2014-02-23
:tags: Pyramid, Pelican, Blog, Python

.. code-block:: python

    def main():
        print 'Hello world!'

    if __name__ == '__main__':
        main()

Now that we have the inevitable first lines out of the way, let's move on. This blog will focus on programming subjects, primarily the `Python <http://python.org>`_ programming language. My current work involves a healthy amount of web framework in the form of `Pyramid <http://www.pylonsproject.org/projects/pyramid/about>`_, which I've become a great fan of. Other parts of the technology stack employed may also feature in articles here.

Aside from work-inspired interests, there are other programming related topics that may feature. I occasionally tinker with Arduinos (most of the code is up on `GitHub <https://github.com/edelooff>`_) and they may feature here. JavaScript, necessary evil that it is, may end up as a subject as well. I'm predicting this based on my many conversations with `herrieii <http://herrieii.nl/>`_ about JavaScript.

Why pelican?
============

  Because I've spent more than enough time postponing the writing part of blogging in lieu of developing something to write my blog with.

The above is not the entire truth of it, but it's definitely a big part of it. Wordpress, though omnipresent and the obvious choice for many, does not fill me with warm feelings. Partly because of its `quite substantial list of vulnerabilities <http://www.cvedetails.com/vulnerability-list/vendor_id-2337/product_id-4096/Wordpress-Wordpress.html>`_ but also because I'd rather not maintain a server running PHP.

I've looked at making my own blog software for quite a while now, but never got around to it; other things proved more interesting. With my recent foray into Pyramid, the thought of creating my own blog came up again. Perhaps with a document-oriented database like Mongo as a backend. It's an entertaining thought, and one that I'm sure will keep surfacing, but ultimately it's a lot of work that distracts from the main purpose of the whole exercise.

When you're not making your own tools, you pick something that's available. In the Python world there's certainly no lack of `blogging software <https://wiki.python.org/moin/PythonBlogSoftware>`_ but nothing stood out as clearly *awesome*. One of the main things that bothered me was the requirement to do blogging in an online fashion. Sure, we live in a world where internet access is omnipresent and you could write partial posts offline, but being forced into a browser just to add a few words to a post? It didn't seem right, and oh, there's all these people doing something with `statically <http://techspot.zzzeek.org/>`_ `generated <http://pydanny.com/>`_ `blogs <http://doughellmann.com/2014/02/16/switching-blogging-platforms-again.html>`_.

Static content generation
=========================

Static content generation, as opposed to dynamic content rendering, is an appealing solution for a blog for a number of reasons:

#. The result of the process is a collection of static files;
#. These static files can be served with minimal latency and server resources;
#. Static content offers zero attack surface for all sorts of exploits;
#. Input for the creation is a collection of ReST or Markdown documents, which are highly portable;
#. The content is easily managed in version control;
#. Compiling and publishing fits my existing deployment workflow.

`Pelican <http://docs.getpelican.com/>`_ offers all of this in a package that was extremely easy to start with. The biggest adjustment is writing content in `reStructuredText <http://docutils.sourceforge.net/rst.html>`_ which I haven't before. The `quick reference <http://docutils.sourceforge.net/docs/user/rst/quickref.html>`_ is fairly comprehensive and easy to understand though, so I don't expect any problems there.

Non-programmers will probably be better off with some form of hosted blogging (`Wordpress <http://wordpress.org/hosting/>`_ or `Blogger <http://www.blogger.com/>`_), but for the programming blogger this seems ideal. I for one am happy with this, blogging software I will actually use.
