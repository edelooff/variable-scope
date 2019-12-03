Aggregating relationships into JSON objects
###########################################

:date: 2019-12-03
:tags: PostgreSQL, Python, SQLAlchemy
:status: published

In day to day use and operation, we strive for a certain degree of normalization_ of the data in our database. In reporting though, this normalization causes some friction: we often *want* the output to contain these duplicates of the data, for sake of row to row completeness. If we're reporting on top-grossing films in the last decade, it's easy enough to join the ``director`` table and list their *name* and *year of birth*. Collecting a set of properties for which we don't know the names and quantity ahead of time is a little more challenging and interesting.

In our example, we'll work with a schema that's a *little* bit like an `Entity–attribute–value model`_, but with strings for both the ``attribute`` and the ``value`` to keep things a little simpler. Of course, we'll pick everyone's favourite tool for bundling arbitrary data: JSON, and collect these properties into a single object.

Before we get into the actual SQL syntax, let's describe the schema we'll be working with:

.. code-block:: postgres

    CREATE TABLE item (
        id SERIAL NOT NULL,
        description TEXT,
        PRIMARY KEY (id))

    CREATE TABLE item_property (
        id SERIAL NOT NULL,
        item_id INTEGER,
        label TEXT,
        value TEXT,
        PRIMARY KEY (id),
        CONSTRAINT uq_property_label UNIQUE (item_id, label),
        FOREIGN KEY(item_id) REFERENCES item (id))

.. PELICAN_END_SUMMARY

Nothing too exciting going on here, but a few observations for sake of completeness:

* Each property has a ``label`` and ``value``;
* Each item has zero or a couple of properties (1-n);
* Each label can only occur once per item (unique).


Wait, why not just load everything?
===================================

We could just load all the items we're interested in, grab all the properties using :py:`subqueryload()` and have SQLAlchemy figure it all out for us. That would certainly save us a bunch of work and is probably what you should do if there's no reason not to.

One of the reasons not to do that, of course, is that everything has to be downloaded to the Python environment. That's going to take a good chunk of memory (and additional time) for large results. For situations like that, server-side cursors are *amazing* (and exposed by SQLAlchemy with the use of :py:`.yield_per()`.) Unfortunately, this approach is `incompatible with eager-loaded collections`__.

__ `sqlalchemy yield per`_

This means that for large datasets, we need some other way of bundling up the collection of properties, because we
probably want to use server-side cursors. Whether you have this need depends on your constraints and the dataset, but let's work on the assumption that the super-easy *load everything* way won't work (or this blog post would be over already.)


How to do this in PostgreSQL
============================

Before going to SQLAlchemy, we need to know the actual query that we want to create. We're going to `aggregate two columns into a JSON object`__ from a joined table. We aggregate everything based on the item's primary key and get the item's basic info as well:

__ `postgresql aggregate functions`_

.. code-block:: postgres

    SELECT
        item.id,
        item.description,
        jsonb_object_agg(ip.label, ip.value) AS "properties"
    FROM item
    JOIN item_property AS ip ON item.id = ip.item_id
    GROUP BY item.id
    ORDER BY item.id;

Keen eyes will have noticed that the ``JOIN`` we're doing is *inner* rather than *left outer*, meaning that we're only accepting items that have at least one property. However, if we also have items without properties that we want to include, we should alter the ``JOIN``` clause. So let's do that and...::

    ERROR:  field name must not be null

Okay, that's a little embarrassing. This happens because the *label* column for the joined *item_property* relation is NULL when there are no properties. So we need to reject NULL values when we construct the JSON object. The ``jsonb_object_agg`` function doesn't provide us with an easy knob for this, so we'll have to pick another `JSON constructing function`__ and have a go at filtering the NULLs out:

__ `postgresql json functions`_

.. code-block:: postgres
    :hl_lines: 4 5 6

    SELECT
        item.id,
        item.description,
        jsonb_object(
            array_agg(ip.label) FILTER (WHERE ip.label IS NOT NULL),
            array_agg(ip.value)) AS "properties"
    FROM item
    LEFT JOIN item_property AS ip ON item.id = ip.item_id
    GROUP BY item.id
    ORDER BY item.id;

Constructing the object is a little more involved now that we can't use its own aggregation, but what we do:

1. We construct an object (using ``jsonb_object``) from an array of keys and an array of values;
2. We use ``array_agg`` to create the *keys* and *values* arrays from the joined relation;
3. We add a  ``FILTER`` clause to filter out NULL keys;

We can skip the ``FILTER`` clause on the *values* because an empty set of keys will stop object creation early, ignoring the values array altogether.


Easy enough, let's do this in SQLAlchemy!
=========================================

We'll first declare the models we'll be working with. The table definitions here are identical to the ones we worked with before, but for completeness we've added a :py:`relationship()`:

.. code-block:: python

    class Item(Base):
        __tablename__ = 'item'
        id = Column(Integer, primary_key=True)
        description = Column(Text)
        properties = relationship('ItemProperty', backref='item')

    class ItemProperty(Base):
        __tablename__ = 'item_property'
        __table_args__ = (
            UniqueConstraint('item_id', 'label', name='uq_property_label'),)
        id = Column(Integer, primary_key=True)
        item_id = Column(ForeignKey('item.id'))
        label = Column(Text)
        value = Column(Text)

First, the query to collect only properties for items that actually have properties (the INNER-join case):

.. code-block:: python

    properties = func.jsonb_object_agg(
        ItemProperty.label, ItemProperty.value)
    items_with_properties = session\
        .query(Item.id, Item.description, properties\
        .join(Item.properties)\
        .group_by(Item.id)

And secondly, the query to get all items and properties where they are present, or :py:`None` when they aren't. We can simply stick a :py:`.filter()` call on the end of the :py:`array_agg()` function call and provide it the relevant filtering clause. The array aggregations are then placed in the :py:`jsonb_object()` call and the SQL constructed is identical to the query we generated before:

.. code-block:: python

    prop_labels = func.array_agg(ItemProperty.label)\
        .filter(ItemProperty.label != null())
    prop_values = func.array_agg(ItemProperty.value)
    properties = func.jsonb_object(prop_labels, prop_values)
    items_with__optional_properties = session\
        .query(Item.id, Item.description, properties)\
        .outerjoin(Item.properties)\
        .group_by(Item.id)


Selecting only *some* labels
============================

Let's assume we have a wide variety of property labels, but we only wish to report on an item's *color* and *shape* (where available). It's tempting to use the :py:`.filter()` clause on the :py:`array_agg()` function for this. However, this will fail with a programming error::

    ERROR:  mismatched array dimensions

The optimization from before (only filtering the keys) has come around to bite us: If either of the arrays passed to ``jsonb_object`` is empty, the function will return a ``null``. But if neither array is empty, they have to be of the *same size*. However, if we add the filter expression to *both* parts of the JSON object construction, everything works as desired:

.. code-block:: python
    :hl_lines: 1 2 3

    label_clause = ItemProperty.label.in_(['color', 'shape'])
    prop_labels = func.array_agg(ItemProperty.label).filter(label_clause)
    prop_values = func.array_agg(ItemProperty.value).filter(label_clause)
    items_and_properties = session.query(
        Item.id,
        Item.description,
        func.jsonb_object(prop_labels, prop_values))\
    .outerjoin(Item.properties)\
    .group_by(Item.id)

Instead of adjusting the filter clause on the aggregation, you could adjust the join condition. Depending on the shape of your data, this may lead to a significant performance improvement. As is often the case though with database performance improvements from asking the question in a slightly different way, measure the difference in performance against your actual database, not against a near-empty example/test database.

.. code-block:: python
    :hl_lines: 8 9 10

    prop_labels = func.array_agg(ItemProperty.label)\
        .filter(ItemProperty.label != null())
    prop_values = func.array_agg(ItemProperty.value)
    items_and_properties = session.query(
        Item.id,
        Item.description,
        func.jsonb_object(prop_labels, prop_values))\
    .outerjoin(ItemProperty, and_(
        Item.properties.expression,
        ItemProperty.label.in_(['color', 'shape']))\
    .group_by(Item.id)

The full join condition for the filtered ItemProperty is derived from the existing relationship's condition (contained in its ``expression`` attribute) and extended with the appropriate condition on the property label.


.. _entity–attribute–value model: https://en.wikipedia.org/wiki/Entity%E2%80%93attribute%E2%80%93value_model
.. _normalization: https://en.wikipedia.org/wiki/Database_normalization
.. _postgresql aggregate functions: https://www.postgresql.org/docs/11/functions-aggregate.html
.. _postgresql json functions: https://www.postgresql.org/docs/11/functions-json.html#FUNCTIONS-JSON-CREATION-TABLE
.. _sqlalchemy yield per: https://docs.sqlalchemy.org/en/13/orm/query.html#sqlalchemy.orm.query.Query.yield_per
