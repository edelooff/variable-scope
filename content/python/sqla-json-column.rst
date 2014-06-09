Creating a JSON column type for SQLAlchemy
##########################################

:date: 2014-04-18
:tags: Python, SQLAlchemy, JSON

.. role:: py(code)
    :language: python
    :class: inline-code

.. class:: post-intro

    This is part one of a two-part post on storage of JSON using SQLAlchemy. This post will touch on the basics of creating a JSON column type and tracking mutability, and is mostly a rehash of the SQLAlchemy documentation. The `second post`__ will cover the tracking of mutability in arbitrarily nested JSON structures, and goes beyond what is covered in the documentation.

__ `nested mutable`_

The past weeks have been pretty busy. We moved from Leeuwarden to Hoofddorp, which in and of itself went pretty smooth, but the new apartment is still very much unfinished. In between work and getting the apartment in order, there hasn't been a lot of time to spend on side projects, but this seemed interesting enough.

A while ago I needed to store a relatively small amount of variable-format data. The requirements are only to store the data, not search in parts of it or anything else. Additionally, it's of such a small volume that it doesn't warrant setting up a document database like MongoDB next to the existing SQLA+Postgres setup. The data itself consisted of a flat mapping of strings to basic scalar types. Something roughly like this:

.. code-block:: python

    {
        'title': 'Example data object',
        'description': 'Information about this example object',
        'storage_location': 'Top shelf in the back',
    }

.. PELICAN_END_SUMMARY


Serializing the data
====================

There are a number of ways to serialize the above, but for sheer ease of use and simplicity, there's nothing that really beats JSON. If the data structures had contained custom types, `pickling <https://docs.python.org/2.7/library/pickle.html>`_ would have been the likely choice. JSON has the additional benefit that because of its simplicity, every programming language in use has a (de)serialization function for it. This makes it extremely portable and allows other tools to work with this data as well.

Creating a type that serializes and deserializes JSON automatically is pretty straight forward and common enough to warrant a section in the `custom types <http://docs.sqlalchemy.org/en/rel_0_9/core/types.html#marshal-json-strings>`_ documentation.

For completeness, I've included the type definition. The highlighted line associates the type with the :py:`class MutableDict` which keeps track of changes to the dictionary. This is covered in the `mutable extension <http://docs.sqlalchemy.org/en/rel_0_9/orm/extensions/mutable.html>`_ documentation.

.. code-block:: python
    :linenos: table
    :hl_lines: 15

    import json
    import sqlalchemy as sqla
    from sqlalchemy.ext import mutable

    class JsonEncodedDict(sqla.TypeDecorator):
      """Enables JSON storage by encoding and decoding on the fly."""
      impl = sqla.String

      def process_bind_param(self, value, dialect):
        return simplejson.dumps(value)

      def process_result_value(self, value, dialect):
        return simplejson.loads(value)

    mutable.MutableDict.associate_with(JsonEncodedDict)


Using the JsonEncodedDict type
==============================

To experiment with the newly defined JSON type, we'll have to set up an initial model and database. For this we'll use an in-memory SQLite database. This is ideal for quick testing because it requires very little effort to set up, and even less to clean up after use.

The following provides just that, or a starting point for something more involved:

.. code-block:: python
    :linenos: table

    import sqlalchemy as sqla
    from sqlalchemy import orm
    from sqlalchemy.ext import declarative

    Base = declarative.declarative_base()

    class FlexibleStorage(Base):
      __tablename__ = 'flexible_storage'
      id = sqla.Column(sqla.Integer, primary_key=True)
      data = sqla.Column(JsonEncodedDict)

      def __init__(self, content):
        self.content = content

    # We set query echoing to True for demonstration purposes
    engine = sqla.create_engine('sqlite://', echo=True)
    Base.metadata.bind = engine
    Base.metadata.create_all()
    session = orm.sessionmaker(bind=engine)()

With the `flexible_storage` table defined and a session created, we can start exploring the possibilities of the JSON type and the included mutation tracking.


Adding and editing records
~~~~~~~~~~~~~~~~~~~~~~~~~~

We create an initial record and provide it with a name.

.. code-block:: python

    bob = FlexibleStorage({'name': 'Bobby'})
    session.add(bob)
    session.commit()

Given we're defining a person, it seems only fair to provide a name and age:

.. code-block:: python

    bob.data['surname'] = 'Selbat'
    bob.data['age'] = 5
    session.commit()

After committing, accessing the record again will trigger a refresh from the database (due to the :py:`expire_on_commit` setting, which defaults to :py:`True`). We'll see that the two fields we added to the record have been persisted to the database (query echoing shows this as well).

This is because the :py:`class MutableDict` we have associated with :py:`class JsonEncodedDict` marked the field as modified as soon as we changed the dictionary. This marking as changed will happen this for :py:`__setitem__` and :py:`__delitem__` methods only. Other methods that change the dictionary in place (like :py:`clear`, :py:`pop`, or :py:`update`) will *not* mark the dictionary as having changed.

Changing the age or removing a surname will both trigger updates of the record (you can see them happen if you set :py:`engine.echo = True`.

.. code-block:: python

    del bob.data['surname']
    session.flush()
    bob.data['age'] = 19
    session.commit()


Nested mutable structures
=========================

The structure we have now is fairly flexible, but also fairly basic. It allows us to store all sorts of information, but what if you have multiple of the same. Storing them as incrementally numbered fields is hardly elegant; we should store them as a list of values. Let's start with that right away:

.. code-block:: python

    bob.data['interests'] = ['computers']
    session.commit()

So far so good, the list was persisted to the database, much as expected. Let's add a second interest to the list and store that:

.. code-block:: python

    bob.data['interests'].append('databases')
    session.commit()
    print bob.data['interests'] # will show only ['computers']

This, unfortunately, is because the change tracking of :py:`class MutableDict` only goes so far. When we alter the interests lists in place, nothing changes on the dictionary. It still contains the same reference to the same list. The latter has just grown a bit. In `the next post`__, we'll have a look at how to track changes throughout arbitrarily nested structures.

__ `nested mutable`_

.. _nested mutable: {filename}sqla-json-nested-mutable.rst
