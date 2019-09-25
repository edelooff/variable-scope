Subset checking in PostgreSQL with SQLAlchemy
#############################################

:date: 2019-09-25
:tags: Python, PostgreSQL, SQLAlchemy
:status: published

Let's assume we have a system where events are stored for multiple services and tenants. Let's also assume that our fictional system has a means of updating many of these events at a time, for instance to mark them as unimportant. And for the sake of keeping things relevant, let's assume that this service is available via some authenticated public API.

Given all of the above, and the knowledge that we can't just trust anyone to limit themselves to events that are theirs to edit, we'll have to verify that all of the events selected for editing are within the scope of editing for the user.

The simplest way to do this would be to load every item from the database and check whether it's eligible for modification. However, this is something that scales terribly past a few dozen records, so let's not even consider that.


Set theory to the rescue
========================

If the phrase "verify a set of given IDs are all part of a set of valid IDs" makes you think of sets and subset checking, you already know what this is about. Python has a ``set`` type that provides a bunch of useful operations that allow us to check whether a given set A (``{1, 4}``) has all of its values present in set B (``{2, 4, 6}``; it does not). We can use this to solve our problem:

.. code-block:: python

    user_selected_ids = {1, 4}
    permissible_ids_q = session.query(Event.id).filter_by(
        service_id=relevant_service,
        tenant_id=current_tenant)
    permissible_event_ids = {row.id for row in permissible_ids_q}
    assert user_selected_ids <= permissible_event_ids

.. PELICAN_END_SUMMARY

The above ORM query selects the Event IDs that are in scope to be edited, fetches all result rows and creates a Python ``set`` from them. Then, we check that all events selected by the user are present in this set.

The good news is that this is pretty easy to understand and will perform reasonably well for anything up to a few hundred or a few thousand events in scope. However, since we're downloading *all* events that are eligible for modification, this won't work if the total set of permissible events is huge.


Moving it to the database
=========================

Instead of bringing a large amount of data to our tools, we can bring our tools to the data. In this case, we will be bringing the subset-checking logic to the database. PostgreSQL has the ``ARRAY`` datatype which has some set-like `functions and operators`__.

__ `Postgres array functions and operators`_

The operator we'll want to use here is ``<@``, which returns whether the left array *is contained by* the right array. With this, we can construct our query from before in pure SQL, and have the database server determine the correct result for us:

.. code-block:: postgres

    SELECT ARRAY[1, 4] <@ ARRAY(
        SELECT id
        FROM event
        WHERE tenant_id = :tenant_id
            AND service_id = :service_id)


Replicating the result in SQLAlchemy
====================================

So now we have a query, great. If we felt particularly uninspired we could wrap it in a :py:`text()` clause and call it a day. However, we don't use a super-powered SQL toolkit to just operate on raw strings, with all the downsides that come with that.

SQLAlchemy has some `support for PostgreSQL types`__, including the array we wish to use. Unfortunately that support is currently limited to *literal* arrays, and not the `array construction from subquery syntax`__ we used in the example on the right-hand side. For now, we'll use a call to :py:`func.array` for that.

__ `SQLAlchemy dialect support for PostgreSQL`_
__ `PostgreSQL array constructor syntax`_

What this looks like is a little bit like this:

.. code-block:: python
    :linenos: table
    :hl_lines: 13 14

    from sqlalchemy.dialects.postgresql import array

    class Event(Base):
        id = Column(Integer, primary_key=True)
        tenant_id = Column(Integer)
        service_id = Column(Integer)

    user_selected_ids = array([1, 4])
    permissible_event_selection = func.array(
        session.query(Event.id)
        .filter_by(service_id=relevant_service, tenant_id=current_tenant)
        .as_scalar())
    valid_event_selection = session.query(
        user_selected_ids.contained_by(permissible_event_selection))
    assert valid_event_selection.scalar()

Before the final assertion on the database query result, a number of things are done to construct that query:

1. On line 8, we set up the literal array for the user's selection (the left hand side of our earlier raw SQL query)
2. On lines 9 through 12 we build the right-hand side array using a query. This selects the Event IDs that are permitted to the current logged in user, and to hint SQLAlchemy that this is a self-contained selection, we select it :py:`.as_scalar()`
3. The final query is constructed on line 13, which uses the named method :py:`.contained_by()` rather than the ``<@`` operator PostgreSQL uses.

.. _PostgreSQL array constructor syntax: https://www.postgresql.org/docs/current/sql-expressions.html#SQL-SYNTAX-ARRAY-CONSTRUCTORS
.. _Postgres array functions and operators: https://www.postgresql.org/docs/current/functions-array.html
.. _SQLAlchemy dialect support for PostgreSQL: https://docs.sqlalchemy.org/en/13/dialects/postgresql.html
