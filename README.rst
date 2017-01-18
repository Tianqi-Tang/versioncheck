=======================
Version Check Decorator
=======================

VERSION: 0.0.1


Introduction
------------

Function decorator that helps do version check and enables function overload
based on versions.

.. code-block:: python

   >>> from versioncheck import version_check



License
-------

`Apache License version 2`_

Installation
------------

You could use "pip" to install "versioncheck".

.. code-block:: bash

    $ pip install versioncheck

Tutorial
--------

Create a version check decorator
````````````````````````````````

To create a version_check decorator, we need to provide a version getter callback
function and a version criteria string.

   - `criteria_string`: The version criteria expression. The supported comparator
     includes: <, <=, =, ==, !=, >, >=, <> (between).

   - `version_getter`: A callback function to retrieve the version. Version check
     decorator will pass below parameters to the callback function:

     - `decorate_type`: Method type

       - `INIT_METHOD`    init method of a decorated class

       - `CLASS_METHOD`    classmethod of a decorated class

       - `STATIC_METHOD`    staticmethod of a decorated class

       - `METHOD`    decorated method/function

     - `\*args and \**kwargs`: The invoke parameters of the decorated method


Below is a simple example:

.. code-block:: python

   >>> from versioncheck import version_check
   >>>
   >>>
   >>> def get_version(decorate_type, *args, **kwargs):
   >>>     # Get version from the named parameters
   >>>     return kwargs.get('version')
   >>>
   >>>
   >>> def my_check(criteria):
   >>>     return version_check(criteria, get_version)
   >>>
   >>>
   >>> @my_check('>2.0')
   >>> def function(version):
   >>>     return 'version > 2.0'
   >>>
   >>>​
   >>> @my_check('<=2.0')  # noqa
   >>> def function(version):
   >>>     return 'version <= 2.0'
   >>>
   >>> function(version='4.0')
   'version > 2.0'
   >>>
   >>> function(version='2.0')
   'version <= 2.0'


Decorate a method/function
``````````````````````````
The decorated method will be executed only if the version criteria is
satisfied, otherwise, `VersionNotSupport` exception is thrown.
The method overload based on versions is supported with using this
decorator. User can defined different versions of methods by decorating
it with different versions criteria. When the method is called, the one
that satisfying the version will be used.

Note that the '# noqa' is needed to get rid of pep8 error.

.. code-block:: python

   >>>  class Resource1(object):
   >>>
   >>>      @staticmethod
   >>>      @my_check('<2.0')
   >>>      def static_method(version):
   >>>          print('static method is invoked.')
   >>>
   >>>      @classmethod
   >>>      @my_check('>=2.0')
   >>>      def class_method(cls, version):
   >>>          print('class method is invoked.')
   >>>
   >>>      @my_check('>2.0')
   >>>      def method(self, version):
   >>>          return 'version > 2.0'
   >>>
   >>>      @my_check('<=2.0')  # noqa
   >>>      def method(self, version):
   >>>          return 'version <= 2.0'
   >>>
   >>>  Resource1.static_method(version="1.1")
   static method is invoked.
   >>>
   >>>  Resource1.static_method(version="3.0")
   VersionNotSupport: API doesn't support version 3.
   >>>
   >>>  Resource1.class_method(version="2.0")
   VersionNotSupport: API doesn't support version 2.
   >>>
   >>>  Resource1.class_method(version="3.0")
   class method is invoked.
   >>>
   >>>  Resource1().method(version="3.0")
   'version > 2.0'
   >>>
   >>>  Resource1().method(version="<=2.0")
   'version <= 2.0'

Decorate a class
````````````````

The decorated class can not be initiated and its static methods and
class methods can not be invoked when the version criteria is not satisfied.

.. code-block:: python

   >>>  @my_check('>3.0')
   >>>  class Resource2(object):
   >>>      def __init__(self, version):
   >>>          self._version = version
   >>>
   >>>  Resource2(version="1.1")
   VersionNotSupport: API doesn't support version 1.1.


.. _Apache License version 2: LICENSE.txt