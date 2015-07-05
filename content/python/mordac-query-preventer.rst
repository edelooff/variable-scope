Mordac the (query) preventer
############################

:date: 2014-09-19
:tags: Python, SQLAlchemy
:status: published

A small update, a much delayed update, but still an update.

A few days ago, cwillu asked the following question in #sqlalchemy [#sqla]_:

::

    <cwillu_> is there a way to entirely disable autocommit?
    <cwillu_> i.e., any insert outside of an explicit transaction
              will either error out, or just immediately rollback?

What eventually worked for this case was simply disabling :py:`autocommit` on the connection level. Explicit rollbacks were issued at the end of each test and all worked fine. But given that SQLAlchemy features a pretty nifty `event system`__, I was pretty sure there was a better solution available. Also, I was waiting for an excuse to experiment with that part of SQLAlchemy, and this offered exactly that.

__ `event documentation`_

As it turns out, preventing queries from happening is about as straightforward as it gets. A quick look at the `list of SQLAlchemy Core events`__ identifies two likely candidates: :py:`'before_cursor_execute'` and :py:`'before_execute'`. Both events are triggered when queries are executed, but the latter is documented to work on a higher level: it's signaled before the query is compiled for the appropriate dialect. Given that we want to entirely prevent queries outside of transactions, stopping them before doing any unnecessary work seems best, so we'll use that one.

__ `core events`_

When the event triggers, our function is called and the caller provides us with the connection and a few other arguments, which we'll collect in :py:`*args`. The `connection`__ has a method  :py:`in_transaction()`, which indicates whether a transaction has explicitly been started for it. That is, even with autocommit turned off, it will return :py:`False` after the first :py:`execute()` call. This is exactly what we need to know and the last thing to do is raise an appropriate error. And so Mordac the Preventer [#mordac]_ is born:

__ `connection api`_

.. PELICAN_END_SUMMARY
.. code-block:: python

    from sqlalchemy.engine import Engine
    from sqlalchemy.event import listens_for

    @listens_for(Engine, 'before_execute')
    def only_permit_transactions(conn, *args):
      if not conn.in_transaction():
        raise Exception('Not allowed to execute outside of a transaction.')

The :py:`Engine` class above could be replaced with the specific engine instance to be restricted, allowing for finer granulated control. For those cases, binding the event handler with a decorator is less practical and the :py:`event.listen()` function should be used: :py:`event.listed(engine, 'before_execute', only_permit_transactions)`.

Using a connection with this event listener attached will allow queries as long as they are part of a transaction. The first example demonstrates a transaction using a context manager:

.. code-block:: python

    >>> engine = sqlalchemy.create_engine('sqlite://')
    >>> with engine.begin() as con:
    ...   print con.execute('SELECT random()').fetchone()
    ...
    (-1062403866648988591,)

Manual start of a transaction with a rollback to mark the end:

.. code-block:: python

    >>> connection = engine.connect()
    >>> transaction = connection.begin()
    >>> print connection.execute('SELECT random()').fetchone()
    (-1625217158689084175,)
    >>> transaction.rollback()

And lastly, attempting to execute a query outside of a transaction:

.. code-block:: python

    >>> print connection.execute('SELECT random()').fetchone()
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
      File "/usr/local/lib/python2.7/dist-packages/sqlalchemy/engine/base.py", line 664, in execute
        params)
      File "/usr/local/lib/python2.7/dist-packages/sqlalchemy/engine/base.py", line 799, in _execute_text
        fn(self, statement, multiparams, params)
      File "/usr/local/lib/python2.7/dist-packages/sqlalchemy/events.py", line 452, in wrap_before_execute
        orig_fn(conn, clauseelement, multiparams, params)
      File "<stdin>", line 4, in only_permit_transactions
    Exception: Not allowed to execute outside of a transaction.

Footnotes
=========

..  [#sqla] The IRC channel on Freenode, where a group of excellent folks provide support for everything to do with SQLAlchemy.
..  [#mordac] *Mordac the Preventer* is a minor recurring character in the *Dilbert* comic by Scott Adams.

..  _connection api: http://docs.sqlalchemy.org/en/rel_0_9/core/connections.html#connection-engine-api
..  _core events: http://docs.sqlalchemy.org/en/rel_0_9/core/events.html
..  _event documentation: http://docs.sqlalchemy.org/en/rel_0_9/core/event.html
