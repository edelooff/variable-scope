Setting eager defaults for SQLAlchemy ORM models
################################################

:tags: Python, SQLAlchemy, defaults
:date: 2020-10-21
:status: published

Default values. We tend to not really think about them. They casually get applied at just the right time when we persist our objects, and everything is right with the universe. Except maybe, sometimes, we need that default value to be there *before* we flush to the database. What if we want the default earlier?


All defaults, all the time
==========================

Let's start with something basic, where we try to eagerly apply as many defaults as we can during construction. SQLAlchemy allows for a `whole host of different defaults`__, but briefly summarized, these are broadly what are accepted:

__ `SQLAlchemy column defaults`_

1. Constant values. Strings, booleans, containers, or any value object
2. SQL expressions. That are executed during flush (e.g. ``sqlalchemy.func.now()``)
3. Python *callables*. These can be of two kinds: simple argument-less functions, or ones that are *context sensitive*, meaning they accept an execution ``context``, which allows access to other columns' values and various other bits.

During object creation, we don't actually interact with the database, so SQL expressions are meaningless, and because Python functions will expect a ``context``, it's easier to just ignore all of them. Constant values it is!

So how do we go about this? Overriding the ``__init__`` method is the obvious first candidate. Unfortunately, that doesn't work due to the internals of the ORM machinery. Thankfully the SQLAlchemy developers have thought of us and there's the option to provide an `alternative constructor`__ during the creation of the ORM Base class. Using this, let's define a Base, our User model and a basic alternative constructor:

__ `Declarative API`_

.. PELICAN_END_SUMMARY

.. code-block:: python
    :linenos: table

    from sqlalchemy import Column, Integer, Text, inspect
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.sql.functions import Function

    def defaults_included_constructor(instance, **kwds):
        mapper = inspect(instance).mapper
        for column in mapper.columns:
            if (default := getattr(column.default, "arg")) is not None:
                if not callable(default) and not isinstance(default, Function):
                    attr = mapper.get_property_by_column(column)
                    kwds.setdefault(attr.key, default)
        for attr, value in kwds.items():
            setattr(instance, attr, value)

    Base = declarative_base(constructor=defaults_included_constructor)

    class User(Base):
        __tablename__ = "user"

        id = Column(Integer, primary_key=True)
        name = Column(Text)
        email = Column(Text)
        role = Column("role_name", Text, default="user")


There, all done, something that works, end of post. Or maybe not? There are some drawbacks to this approach. Mainly, it's a bit overly broad and aggressive on eagerly applying defaults. An approach that provides a little bit more *finesse* would be nice.

A more selective default
========================

Given there's already instance checks in there, the most immediately appealing and *easy* thing is to create a new ``EagerDefault`` type and roll with that. As a bonus, the filtering down to our desired class of default is easier and more

.. code-block:: python
    :linenos: table

    from sqlalchemy import Column, Integer, Text, inspect
    from sqlalchemy.ext.declarative import declarative_base

    class EagerDefault:
        def __init__(self, value: Any):
            self.value = value

    def defaults_included_constructor(instance, **kwds):
        mapper = inspect(instance).mapper
        for column in mapper.columns:
            if (default := getattr(column.default, "arg")) is not None:
                if isinstance(default, EagerDefault):
                    attr = mapper.get_property_by_column(column)
                    kwds.setdefault(attr.key, default.value)
        for attr, value in kwds.items():
            setattr(instance, attr, value)

    Base = declarative_base(constructor=defaults_included_constructor)

    class User(Base):
        __tablename__ = "user"

        id = Column(Integer, primary_key=True)
        name = Column(Text)
        email = Column(Text)
        role = Column("role_name", Text, default=EagerDefault("user"))


It's more selective, but now we've introduced a new class, a new type and API (even if it's very simple), which depending on your point of view is perfectly okay, or something to be `avoided by any reasonable means`__. Also, the implementation still goes over all columns and does a lot of work for potentially exactly zero results. We've optimized for the developer, not the *user* of this code.

__ `stop writing classes`_


User-specified eager defaults
=============================

There are a number (maybe even an *endless* number) or ways to make eager defaults that are convenient for the user of the code. Changing the ``Column`` type is one, but it's a pretty aggressive one, that affects *every* column rather than just the ones with defaults that should be eager. Let's rule that out.

Another solution is to have a *dunder* class attribute that specifies the attribute names that should be eagerly resolved. It's highly targeted, completely opt-in, minimally intrusive, and easy to understand. It ticks all the boxes that I just make up on the spot, so it's definitely today's favorite solution:

.. code-block:: python
    :linenos: table

    from sqlalchemy import Column, Integer, Text
    from sqlalchemy.ext.declarative import declarative_base

    def defaults_included_constructor(instance, **kwds):
        for attr, value in kwds.items():
            setattr(instance, attr, value)
        for attr in set(getattr(instance, "__eager_defaults__", ())) - set(kwds):
            column = getattr(type(instance), attr)
            setattr(instance, attr, column.default.arg)

    Base = declarative_base(constructor=defaults_included_constructor)

    class User(Base):
        __eager_defaults__ = ("role",)
        __tablename__ = "user"

        id = Column(Integer, primary_key=True)
        name = Column(Text)
        email = Column(Text)
        role = Column("role_name", Text, default="user")


The constructor code got a little bit shorter, but more importantly it does a *lot less work*:

#. It will only process columns that the developer has explicitly indicated should have eager defaults
#. Moreover, it will will skip those that have explicitly been assigned values (line 7)

Because we can directly access attributes, rather than columns, we can leave out the ``inspect`` call and directly access the model itself to retrieve the column (line 8) and set the default value line 9).

It is now the caller's responsibility to indicate the columns to set eager defaults for. This gives them explicit control, but also means that the implementation doesn't have to explicitly check each value for suitability. If the caller makes a mistake and provides a relationship or other non-``Column`` as a default? They'll get an error, but the stack trace should make it easy enough to see what went wrong. A single check at class creation might be nice, but that's left as an exercise for the reader.


.. _Declarative API: https://docs.sqlalchemy.org/en/13/orm/extensions/declarative/api.html#sqlalchemy.ext.declarative.declarative_base
.. _SQLAlchemy column defaults: https://docs.sqlalchemy.org/en/13/core/defaults.html#column-insert-update-defaults
.. _Stop writing classes: https://www.youtube.com/watch?v=o9pEzgHorH0