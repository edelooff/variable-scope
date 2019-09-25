Mutation tracking in nested JSON structures using SQLAlchemy
############################################################

:date: 2014-04-20
:tags: Python, SQLAlchemy, JSON
:status: published

.. class:: post-intro

    This is part two of a two-part post on storage of JSON using SQLAlchemy. The `first post <{static}/python/sqla-json-column.rst>`_ covered the basics of creating a JSON column type and tracking mutations. In this post, we will continue from there to cover mutation tracking in arbitrarily nested structures.

In the previous post we ended with an example of appending to an existing list. Upon committing the changes in the session and reloading the object, it was shown the appended string had not been stored. This happened because changing the list in-place did not trigger the :py:`changed()` method of the :py:`class MutableDict`. Only setting or deleting a key from the dictionary marks it as changed, and marking it as changed upon access (which is all we did on the dictionary itself) would cause far too many updates of the database.

What we wanted (and perhaps expected) is behavior where changing the list marks the dictionary it's part of as changed. And for completeness, if the dictionary contained a number of nested dictionaries, changing any of them at any level should mark the :py:`class MutableDict` as changed. To achieve this, we need a solution that consists of the following parts:

#. Replacement types for :py:`list` and :py:`dict` where all methods that change the object in-place flag it as having changed.
#. A means to propagate the notification of change up to the top so that it reaches the :py:`class MutableDict`.
#. Conversion of all mutable types to the defined replacement types. Both when they are added to the existing structure, as well as on load from the database.

.. PELICAN_END_SUMMARY


Objects that track mutation
===========================

This step mainly consists of subclassing the existing :py:`list` and :py:`dict` types and adding a call to a :py:`changed()` method whenever one of the methods that alters the object is called. Given that we're adding this functionality to both classes, the code duplication can be reduced a little by making both inherit from a single parent: the :py:`TrackedObject`:

.. code-block:: python
    :linenos: table

    class TrackedObject(object):
      def changed(self):
        """Marks the object as changed."""
        print '<%s object at %0xd> has changed' % (
            type(self).__name__, id(self))


    class TrackedDict(TrackedObject, dict):
      """A TrackedObject implementation of the basic dict."""
      def __setitem__(self, key, value):
        self.changed()
        super(TrackedDict, self).__setitem__(key, value)

      def __delitem__(self, key):
        self.changed()
        super(TrackedDict, self).__delitem__(key)

      def clear(self):
        self.changed()
        super(TrackedDict, self).clear()

      def pop(self, *key_and_default):
        self.changed()
        return super(TrackedDict, self).pop(*key_and_default)

      def popitem(self):
        self.changed()
        return super(TrackedDict, self).popitem()

      def update(self, source=(), **kwds):
        self.changed()
        super(TrackedDict, self).update(source, kwds)


    class TrackedList(TrackedObject, list):
      """A TrackedObject implementation of the basic list."""
      def __setitem__(self, key, value):
        self.changed()
        super(TrackedList, self).__setitem__(key, value)

      def __delitem__(self, key):
        self.changed()
        super(TrackedList, self).__delitem__(key)

      def append(self, item):
        self.changed()
        super(TrackedList, self).append(item)

      def extend(self, iterable):
        self.changed()
        super(TrackedList, self).extend(iterable)

      def pop(self, index):
        self.changed()
        return super(TrackedList, self).pop(index)

As you may have spotted in the definitions above, there are a few shortcomings in the interest of keeping the code clean and concise:

#. A couple of methods that alter the object in-place have been left out;
#. Objects are marked as changed even if an error prevents the actual change from happening.

However, while the example is minimal and assumes an ideal environment in which no errors occur, it makes for a good starting point for the rest of the example.


Propagating changes
===================

The second part we identified as important for this to work is the need to have changes propagate up the nested structure. we now have a method :py:`changed()` that gets called whenever a change has occurred, and we need to make sure it communicates upward. For this, we will redefine our :py:`class TrackedObject`:

.. code-block:: python
    :linenos: table

    import logging

    class TrackedObject(object):
      def __init__(self, *args, **kwds):
        self.logger = logging.getLogger('TrackedObject')
        self.logger.debug('%s: intialized' % self._repr())
        self.parent = None
        super(TrackedObject, self).__init__(*args, **kwds)

      def changed(self):
        """Used to mark the object as changed.

        If a `parent` attribute is set, the `changed()` method
        on the parent will be called, propagating the notification.
        """
        self.logger.debug('%s: changed' % self._repr())
        if self.parent is not None:
          self.parent.changed()

      def _repr(self):
        """Simple object representation"""
        return '<%s object at 0x%0xd>' % (type(self).__name__, id(self))

The parent container will now be notified of any changes to the tracked object, but there's no code yet to set the parent. We'll do that next.


Converting mutable types
========================

Setting the parent of the tracked object is something to do at creation. Creation of these items will (mainly) be done by converting from the regular to the tracked type. We'll convert :py:`lists` to :py:`TrackedList` and :py:`dicts` to :py:`TrackedDict`. The straight forward solution for that is to define a function that does these two conversions for us:

.. code-block:: python

    def convert_to_tracked(obj, parent):
      if type(obj) == dict:
        obj = TrackedDict(obj)
        obj.parent = parent
      elif type(obj) == list:
        obj = TrackedList(obj)
        obj.parent = parent
      return obj

Another way, which allows for additional tracked types and less static coding is to add a decorator classmethod to the :py:`class TrackedObject` and decorating the implementations of it:

.. code-block:: python

    class TrackedObject(object):
      # everything defined previously ...
      _type_mapping = {}

      @classmethod
      def register(cls, origin_type):
        """Registers the decorated class as a type replacement."""
        def decorator(tracked_type):
          cls._type_mapping[origin_type] = tracked_type
          return tracked_type
        return decorator

      @classmethod
      def convert(cls, obj, parent):
        """Converts registered types to types."""
        obj_type = type(obj)
        for origin_type, replacement in cls._type_mapping.iteritems():
          if obj_type is origin_type:
            new = replacement(obj)
            new.parent = parent
            return new
        return obj

    @TrackedObject.register(dict)
    class TrackedDict(TrackedObject, dict):
      # no changes to the class body

    @TrackedObject.register(list)
    class TrackedList(TrackedObject, list):
      # no changes to the class body

Now that the TrackedObject has a classmethod to convert any object to a registered tracked variant, the third and last part is a matter of using it.


All mutable types will be tracked types
=======================================

Whenever we add an item to a tracked mutable object, if the added object itself is a mutable, it will have to be converted to a tracked type. This means that we will have to revisit the mutating methods on the :py:`class TrackedDict` and :py:`class TrackedList`. Specifically, those methods that *add* items.

The changes are fairly straightforward (and repetitive), so we'll highlight a few of them:

.. code-block:: python

      def append(self, item):
        self.changed()
        super(TrackedList, self).append(item)

      def extend(self, iterable):
        self.changed()
        super(TrackedList, self).extend(iterable)

      def update(self, source=(), **kwds):
        self.changed()
        super(TrackedDict, self).update(source, kwds)

Are replaced with methods that run the convert method on all the added values:

.. code-block:: python

      def append(self, item):
        self.changed()
        super(TrackedList, self).append(self.convert(item, self))

      def extend(self, iterable):
        self.changed()
        super(TrackedList, self).extend(
            self.convert(item, parent) for item in iterable)

      def update(self, source=(), **kwds):
        if source:
          self.changed()
          if isinstance(source, dict):
            source = source.iteritems()
          super(TrackedDict, self).update(
            (key, self.convert(val, self)) for key, val in source)
        if kwds:
          self.update(kwds)

#. The :py:`TrackedList.append()` method converts the single item and adds it using :py:`list.append()`
#. The list :py:`TrackedList.extend()` method sets up a generator to convert all items, letting the original :py:`list.extend()` method process it.
#. The :py:`TrackedDict.update()` method allows for either a dictionary or 2-tuple iterator argument, as well as additional keyword arguments. The latter themselves make up a dictionary which we process in a recursive update run. The actual updating is done by reducing the problem to a 2-tuple iterator where the value is converted, and the whole is processed by the :py:`dict.update()`.


Extending the SQLA MutableDict
==============================

With all of these parts taken care of, it's time to put in place the last piece. In the first post we used :py:`mutable.MutableDict` to track the changes made to the :py:`JsonEncodedObject`. We need the same functionality here, with the additional behavior that all items added are converted to tracked types. The easiest way to do that is to ensure that our :py:`MutableDict` replacement itself is derived from :py:`TrackedDict`.

.. code-block:: python
    :linenos: table

    import sqlalchemy
    from sqlalchemy.ext import mutable

    class NestedMutable(mutable.MutableDict, track.TrackedDict):
      """MutableDict extension for nested change tracking."""
      def __setitem__(self, key, value):
        """Convert values to change-tracking types where available."""
        super(NestedMutable, self).__setitem__(
            key, self.convert(value, self))

      @classmethod
      def coerce(cls, key, value):
        """Convert plain dictionary to NestedMutable."""
        if isinstance(value, cls):
          return value
        if isinstance(value, dict):
          return cls(value)
        return super(cls).coerce(key, value)

    class NestedJsonObject(sqlalchemy.TypeDecorator):
      """Enables JSON storage by encoding and decoding on the fly."""
      impl = sqlalchemy.String

      def process_bind_param(self, value, dialect):
        return json.dumps(value)

      def process_result_value(self, value, dialect):
        return json.loads(value)


    NestedMutable.associate_with(NestedJsonObject)

After defining the NestedMutable type, that, we define a new JSON column type. This one is functionally the same as the *simple* mutable JsonObject, but after associating it with the NestedMutable type, it will track changes at any level of nesting.

This is when we can start using it in a table definition and edit away. Whenever a change is made anywhere in the JSON structure, the next :py:`flush()` or :py:`commit()` will trigger an UPDATE query to run on the database, storing your data.

The complete and resulting code for this blog post can be found on the GitHub project: `SQLAlchemy-JSON <https://github.com/edelooff/sqlalchemy-json>`_.
