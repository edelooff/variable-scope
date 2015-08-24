Storing and verifying passwords with SQLAlchemy
###############################################

:tags: Python, SQLAlchemy, bcrypt, passwords

I really enjoy abstractions.

Abstractions are the lifeblood of programming. They take complex operations and make them easy to work with through accessible interfaces. This article will be about doing that with the way we store and verify passwords (or rather their cryptographic hashes) in (web-)applications based on SQLAlchemy. And in such a way that we can upgrade the security of passwords as old encryption schemes are broken or proven insufficient and new ones get introduced.


The ways of verifying passwords
===============================

There are many different ways to deal with password verification, but they can be classified in three rough categories:


Ad-hoc verification
-----------------------

This approach is often used for one-off scripts or trivial applications that have a single verification and have very little to gain from reusable components. The following shows a very basic User model and password verification code:

.. code-block:: python

    import bcrypt
    from sqlalchemy import Column, Integer, Text

    class User(Base):
        __tablename__ = 'user'
        id = Column(Integer, primary_key=True)
        name = Column(Text)
        password = Column(Text)

    pwhash = bcrypt.hashpw(login_data['password'], user.password)
    if user.password == pwhash:
        print 'Access granted'

The snippet above uses the Python bcrypt_ package for key derivation, but you may well use another key derivation method, like PBKDF2_ or scrypt_. To be sure: It should not have a static salt, and it should *definitely not* be a single round of optimized-for-speed SHA1 or SHA2 functions. [#fast-hashes]_ In short, use proven and existing methods.

Assuming that the hashing algorithm is secure, this code is perfectly fine for the stated goal. However, most applications are *not* trivial and most one-off scripts tend to find their way into repeated use. And over time you find yourself confronted with more and more repeats of the same code to verify a user's password. Something needs to be done, it's time to refactor this.


Delegated password verification
-------------------------------

Your application has grown and there are now a number of places where a user's password needs to be verified. There is the login page, but also when changing sensitive settings, or changing the user's password, and maybe a few more. Having the same block of code repeated throughout the application is a maintenance problem waiting to happen, so the verification is delegated.

In this case, it's delegated to the :py:`class User`. A method is added that checks the current password hash to the one calculated for the login attempt and returns whether or not they are the same:

.. code-block:: python
    :hl_lines: 10 11 12

    import bcrypt
    from sqlalchemy import Column, Integer, Text

    class User(Base):
        __tablename__ = 'user'
        id = Column(Integer, primary_key=True)
        name = Column(Text)
        password = Column(Text)

        def verify_password(self, password):
            pwhash = bcrypt.hashpw(password, self.password)
            return self.password == pwhash

    if user.verify_password(login_data['password']):
        print 'Access granted'

With this verification method on the user, all password checks can be delegated to a single routine. If any changes to the password storage or verification need to be made, this only needs to be done once, in one place. Problem solved? Mostly. While the above certainly works and is a significant improvement over the ad-hoc solution, there are still a couple of issues that remain:

1. Multiple models may need password verification; your application may have separate models for regular and administrative users, or include other primitives that require passwords. Each of these would need its own verification method. One solution to this is applying a single mixin class that deals with password verification.
2. Password *setting* still needs to be handled. This could be done using a :py:`@validates` decorator which takes care of creating the hash. To make it reusable, adding it to the above mentioned mixin class would be a good idea.
3. Mainly, I think it's an inelegant abstraction that needlessly exposes implementation details (bcrypt) and could have a much more intuitive interface.


Making password hashes intelligent
----------------------------------

The *much more intuitive interface* for verification is a **comparison** rather than a function call. What we want to achieve is to check whether the provided password is equal to the one we have (even if we can only really compare the plaintext with a hash). For this, we can write a fairly simple class that takes a bcrypt hash which provides its own equality comparator.

.. code-block:: python
    :linenos: table

    import bcrypt

    class PasswordHash(object):
        def __init__(self, hash_):
            assert len(hash_) == 60, 'bcrypt hash should be 60 chars.'
            assert hash_.count('$'), 'bcrypt hash should have 3x "$".'
            self.hash = str(hash_)
            self.rounds = int(self.hash.split('$')[2])

        def __eq__(self, candidate):
            """Hashes the candidate string and compares it to the stored hash."""
            if isinstance(candidate, basestring):
                if isinstance(candidate, unicode):
                    candidate = candidate.encode('utf8')
                return bcrypt.hashpw(candidate, self.hash) == self.hash
            return False

        def __repr__(self):
            """Simple object representation."""
            return '<{}>'.format(type(self).__name__)

        @classmethod
        def new(cls, password, rounds):
            """Creates a PasswordHash from the given password."""
            if isinstance(password, unicode):
                password = password.encode('utf8')
            return cls(bcrypt.hashpw(password, bcrypt.gensalt(rounds)))


Creating a new PasswordHash can be done from either a plaintext password using the :py:`new()` classmethod, or from an existing hash by just instantiating it. Comparing the now existing hash with a plaintext password is as simple and clear as it gets:

.. code-block:: python

    if user.password == login_data['password']:
        print 'Access granted'

This *does* assume that the ``password`` member of the user object is an instance of our :py:`class PasswordHash`. That's easily achieved by using the SQLAlchemy type extension system.


Using PasswordHash in your SQLAlchemy model
===========================================

A password hash is essentially a simple string. All that we want to do is ensure that the hash encapsulated in our PasswordHash is stored in the database, and that a PasswordHash object is returned when we read a hash from the database. For this, SQLAlchemy provides us with TypeDecorators__. These allow exactly the kind of augmentations we want to bestow on our new Password type.

__ `sqla typedecorator`_

Using the TypeDecorator building block, we construct a new Password type that we can use in column specifications. There are a few things that we need to take care of:

1. Choose a database type to extend. For this example I've gone with ``Text`` but depending on the underlying database there might be a better type for you.
2. A way to convert the PasswordHash object to a value suitable for the implementor type. This is the :py:`process_bind_param()` method.
3. A way to convert the database value to a PasswordHash we want to use in the Python runtime. This is the :py:`process_result_value()` method.

.. code-block:: python
    :linenos: table
    :hl_lines: 44 46 47 48

    from sqlalchemy import Column, Integer, Text, TypeDecorator
    from sqlalchemy.orm import validates

    class Password(TypeDecorator):
        """Allows storing and retrieving password hashes using PasswordHash."""
        impl = Text

        def __init__(self, rounds=12, **kwds):
            self.rounds = rounds
            super(Password, self).__init__(**kwds)

        def process_bind_param(self, value, dialect):
            """Ensure the value is a PasswordHash and then return its hash."""
            return self._convert(value).hash

        def process_result_value(self, value, dialect):
            """Convert the hash to a PasswordHash, if it's non-NULL."""
            if value is not None:
                return PasswordHash(value)

        def validator(self, password):
            """Provides a validator/converter for @validates usage."""
            return self._convert(password)

        def _convert(self, value):
            """Returns a PasswordHash from the given string.

            PasswordHash instances or None values will return unchanged.
            Strings will be hashed and the resulting PasswordHash returned.
            Any other input will result in a TypeError.
            """
            if isinstance(value, PasswordHash):
                return value
            elif isinstance(value, basestring):
                return PasswordHash.new(value, self.rounds)
            elif value is not None:
                raise TypeError(
                    'Cannot convert {} to a PasswordHash'.format(type(value)))

    class User(Base):
        __tablename__ = 'user'
        id = Column(Integer, primary_key=True)
        name = Column(Text)
        password = Column(Password)
        # Or specify a cost factor other than the default 12
        # password = Column(Password(rounds=10))

        @validates('password')
        def _validate_password(self, key, password):
            return getattr(type(self), key).type.validator(password)


The :py:`@validates` decorator is optional but ensures that the password value is converted to a ``PasswordHash`` as soon as it is assigned, and does not require committing the session before it's visible. This does move the expense of the hashing forward to the moment of assignment rather than the moment of flushing. It also means there's never a plaintext value stored on the user object, which means it can't accidentally leak, which is definitely a bonus.

One other thing to note about the Password type is that it allows the configuration of the key derivation complexity in the column definition. This way we can determine how costly (slow, safe) our key derivation should be. Higher numbers will rapidly increase the cost of comparison, so this will depend on how often passwords are expected to be used, renewed and what they provide access to.


A HasPassword mixin
-------------------

When listing the disadvantages of the :py:`User.verify_password()` method, I mentioned some of the reuse of code could be established with a mixin class. This can still be achieved with the solution above, making use of SQLAlchemy's support for `mixin columns`_.

The following snippet defines such a mixin which is then used by two models User and ProtectedFile. Both of these models will have a ``password`` column attribute, including the validator that converts strings to proper :py:`class PasswordHash` instances.

.. code-block:: python

    class HasPassword(object):
        password = Column(Password)

        @validates('password')
        def _validate_password(self, key, password):
            return getattr(type(self), key).type.validator(password)

    class User(HasPassword, Base):
        __tablename__ = 'user'
        id = Column(Integer, primary_key=True)
        name = Column(Text)

    class ProtectedFile(HasPassword, Base):
        __tablename__ = 'protected_file'
        id = Column(Integer, primary_key=True)
        filename = Column(Text)


Supporting upgradeable key strength
===================================

As computers get significantly faster each year, and access to large clusters of computers is getting easier as well, there are strong incentives to be able to upgrade our password hashing complexity. What was a comfortable number of rounds five years ago, is a lot easier to crack with a brute force attack today. Having the option to upgrade the complexity of our hashing is crucial for any system that is going to last any length of time.

The ``Password`` type in the model definition can be given a different (higher) ``rounds`` parameter. However, that will only ensure *new* passwords are created with this increased complexity, it does nothing for the existing hashes. What we can make is a system where the hash is upgraded whenever it is verified and proves to be correct. Due to the one-way nature of cryptographic hashing, we can't easily upgrade them without knowing the plaintext that created the hash in the first place.

Updating the internal hash after verifying the password is correct is nice and all, but it won't cause the database to be updated all by itself. This is because SQLAlchemy by default only monitors assignments to the column attributes of a record. When an already assigned value is changed internally, this will not be picked up and SQLAlchemy will not update the database upon flush or commit. Tracking and marking of internal changes is made possible by extending a type using the `mutable extension`_.


A mutable PasswordHash
----------------------

Making our :py:`class PasswordHash` a ``Mutable`` type allows us to mark it as having changed when we update the internal hash. For this, we need to make a few changes:

.. code-block:: python
    :linenos: table
    :hl_lines: 1 2 7 19 20 21 22

    class PasswordHash(Mutable):
        def __init__(self, hash_, rounds=None):
            assert len(hash_) == 60, 'bcrypt hash should be 60 chars.'
            assert hash_.count('$'), 'bcrypt hash should have 3x "$".'
            self.hash = str(hash_)
            self.rounds = int(self.hash.split('$')[2])
            self.desired_rounds = rounds or self.rounds

        def __eq__(self, candidate):
            """Hashes the candidate string and compares it to the stored hash.

            If the current and desired number of rounds differ, the password is
            re-hashed with the desired number of rounds and updated with the results.
            This will also mark the object as having changed (and thus need updating).
            """
            if isinstance(candidate, basestring):
                if isinstance(candidate, unicode):
                    candidate = candidate.encode('utf8')
                if self.hash == bcrypt.hashpw(candidate, self.hash):
                    if self.rounds < self.desired_rounds:
                        self._rehash(candidate)
                    return True
            return False

        def __repr__(self):
            """Simple object representation."""
            return '<{}>'.format(type(self).__name__)

        @classmethod
        def coerce(cls, key, value):
            """Ensure that loaded values are PasswordHashes."""
            if isinstance(value, PasswordHash):
                return value
            return super(PasswordHash, cls).coerce(key, value)

        @classmethod
        def new(cls, password, rounds):
            """Returns a new PasswordHash object for the given password and rounds."""
            if isinstance(password, unicode):
                password = password.encode('utf8')
            return cls(cls._new(password, rounds))

        @staticmethod
        def _new(password, rounds):
            """Returns a new bcrypt hash for the given password and rounds."""
            return bcrypt.hashpw(password, bcrypt.gensalt(rounds))

        def _rehash(self, password):
            """Recreates the internal hash and marks the object as changed."""
            self.hash = self._new(password, self.desired_rounds)
            self.rounds = self.desired_rounds
            self.changed()

A number of things were changed:

1. Inheriting from **Mutable** allows signaling of the internal change of state that needs to be persisted.
2. To know whether or not to upgrade, the *desired* complexity needs to be set and stored next to the hash's current complexity.
3. When the provided password is correct, check the desired complexity against the current. If the current complexity is too low, we rehash the password, update the complexity and mark the change.
4. The ``coerce()`` method is part of the required interface of Mutable. It doesn't do much for this class but is required nonetheless.
5. To reuse code, ``_new()`` is now responsible for creating a new bcrypt hash from a plaintext and complexity argument.


Changes to Password
-------------------

The SQLAlchemy :py:`class Password` needs only a small change to work with the new mutable ``PasswordHash``. The desired complexity needs to be provided whenever a password hash is loaded from the database, leading to the following small change:

.. code-block:: python
    :linenos: table
    :hl_lines: 16

    class Password(TypeDecorator):
        """Allows storing and retrieving password hashes using PasswordHash."""
        impl = Text

        def __init__(self, rounds=12, **kwds):
            self.rounds = rounds
            super(Password, self).__init__(**kwds)

        def process_bind_param(self, value, dialect):
            """Ensure the value is a PasswordHash and then return its hash."""
            return self._convert(value).hash

        def process_result_value(self, value, dialect):
            """Convert the hash to a PasswordHash, if it's non-NULL."""
            if value is not None:
                return PasswordHash(value, rounds=self.rounds)

        def validator(self, password):
            """Provides a validator/converter for @validates usage."""
            return self._convert(password)

        def _convert(self, value):
            """Returns a PasswordHash from the given string.

            PasswordHash instances or None values will return unchanged.
            Strings will be hashed and the resulting PasswordHash returned.
            Any other input will result in a TypeError.
            """
            if isinstance(value, PasswordHash):
                return value
            elif isinstance(value, basestring):
                return PasswordHash.new(value, self.rounds)
            elif value is not None:
                raise TypeError(
                    'Cannot convert {} to a PasswordHash'.format(type(value)))


Upgrading the hash strength
---------------------------

To upgrade the key derivation complexity, all we now have to do is provide an upgraded ``rounds`` parameter. This will upgrade the password hashes of active users over time, without requiring ad-hoc code for each migration.

.. code-block:: python
    :linenos: table
    :hl_lines: 5

    class User(Base):
        __tablename__ = 'user'
        id = Column(Integer, primary_key=True)
        name = Column(Text)
        password = Column(Password(rounds=13))

        @validates('password')
        def _validate_password(self, key, password):
            return getattr(type(self), key).type.validator(password)

    # Create plain user with default key complexity
    john = User(name='John', password='flatten-shallow-ideal')

    # Create an admin user with higher key derivation complexity
    administrator = User(
        name='Simon',
        password=PasswordHash.new('working-as-designed', 15))

As shown in the example creation of the 'administrator' user, the ``Password`` type also allows for stronger hashes on an individual basis. This works because the rehashing of the password is only performed when the current complexity is *under* the set threshold. Hashes with a higher complexity than the configured lower bound are left untouched.

This approach adds complexity to the password setting of an account, but can be used to selectively increase the cost of comparison. The added complexity in this case makes any comparison an additional four times slower (given the exponential cost scaling of bcrypt). While this slows down the password verification step, it pushes the same cost to an attacker attempting to crack the password. A hundred or so milliseconds for a verification will hardly be noticeable, but slows down a brute-force attack to a snail's pace.


Further improvements
--------------------

In a follow-up article we'll have a look at an even more flexible password upgrade solution. One that supports both bcrypt and the example single-iteration salted SHA1, and upgrades them as they are accessed, allowing for a smooth migration for all active users.


Footnotes
=========

..  [#fast-hashes] This isn't a new concern, but with the rising popularity of Bitcoin and derivatives, breaking hashes is getting exponentially cheaper and faster. See also: `http://www.matasano.com/log/958/enough-with-the-rainbow-tables-what-you-need-to-know-about-secure-password-schemes/`__

__ `enough with the rainbow tables`_

..  _bcrypt: https://github.com/pyca/bcrypt/
..  _enough with the rainbow tables: http://web.archive.org/web/20080822090959/http://www.matasano.com/log/958/enough-with-the-rainbow-tables-what-you-need-to-know-about-secure-password-schemes/
..  _mixin columns: http://docs.sqlalchemy.org/en/rel_1_0/orm/extensions/declarative/mixins.html#mixing-in-columns
..  _mutable extension: http://docs.sqlalchemy.org/en/rel_1_0/orm/extensions/mutable.html
..  _pbkdf2: https://en.wikipedia.org/wiki/PBKDF2
..  _scrypt: https://en.wikipedia.org/wiki/Scrypt
..  _sqla typedecorator: http://docs.sqlalchemy.org/en/rel_1_0/core/custom_types.html#augmenting-existing-types
