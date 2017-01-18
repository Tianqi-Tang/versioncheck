# coding=utf-8
# Copyright (c) 2016 EMC Corporation.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
from __future__ import unicode_literals

from distutils.version import LooseVersion
import inspect
import six

import versioncheck.exceptions as ex


_op_mapping_ = {}


class Criteria(object):
    def __init__(self, op, sentry, sentry2=None):
        self.op = self.get_op(op)
        self.sentry = sentry
        self.sentry2 = sentry2

    def _support_op(*args):
        """Internal decorator to define an criteria compare operations."""
        def inner(func):
            for one_arg in args:
                _op_mapping_[one_arg] = func
            return func

        return inner

    def test(self, other):
        if other is None:
            return True
        return self.op(self, six.text_type(other))

    @_support_op('=', '==')
    def _eq(self, other):
        return self.sentry == LooseVersion(other)

    @_support_op('<>')
    def _between(self, other):
        return self.sentry < LooseVersion(other) < self.sentry2

    @_support_op('<')
    def _lt(self, other):
        return LooseVersion(other) < self.sentry

    @_support_op('>')
    def _gt(self, other):
        return LooseVersion(other) > self.sentry

    @_support_op('>=')
    def _ge(self, other):
        return LooseVersion(other) >= self.sentry

    @_support_op('<=')
    def _le(self, other):
        return LooseVersion(other) <= self.sentry

    @_support_op('!=')
    def _ne(self, other):
        return LooseVersion(other) != self.sentry

    @classmethod
    def get_op(cls, op_str):
        if op_str not in _op_mapping_:
            raise ex.InvalidCriteriaOperation(op=op_str)
        return _op_mapping_[op_str]

    @classmethod
    def parse(cls, criteria_str):
        # Sorted the supported ops by length. The longer one goes first.
        support_ops = sorted(_op_mapping_.keys(), key=len, reverse=True)
        for op in support_ops:
            if criteria_str.find(op) != -1:
                fields = criteria_str.split(op)
                sentrys = [LooseVersion(field.strip()) for field in fields if
                           len(field.strip()) != 0]
                return cls(op, *sentrys)
        else:
            raise ex.InvalidVersionCriteria(criteria=criteria_str)


class VersionedFuncManager(object):
    __func_mapping__ = {}

    @classmethod
    def add_func(cls, key, versioned_func):
        cls.__func_mapping__.setdefault(key, []).append(versioned_func)

    @classmethod
    def get_support_func(cls, key, version):
        all_funcs = cls.__func_mapping__[key]
        valid_func = [func.func for func in all_funcs if func.support(version)]
        if len(valid_func) == 0:
            raise ex.VersionNotSupport(version=version)
        return valid_func[-1]

    @staticmethod
    def get_function_name(func):
        if six.PY2:
            if hasattr(func, "im_class"):
                return "%s.%s" % (func.im_class, func.__name__)
            else:
                return "%s.%s" % (func.__module__, func.__name__)
        else:
            return "%s.%s" % (func.__module__, func.__qualname__)


class VersionedFunc(object):
    def __init__(self, criteria, func):
        self.criteria = criteria
        self.func = func

    def support(self, version):
        return self.criteria.test(version)


class Check(object):
    """Version requirement decorator

    This is a version validation decorator and can apply to either a
    Class, funciont or a method. When apply it to a method/function,
    it supports function overload based on versions.

    :param criteria_string: The version criteria expression. The supported
     comparator includes: <, <=, =, ==, !=, >, >=, <>(between)
    :param version_getter: A callback function to retrieve the version. Check
     decorator will pass below parameters to the callback:
        decorate_type: Method type
           - INIT_METHOD    init method of a decorated class
           - CLASS_METHOD   classmethod of a decorated class
           - STATIC_METHOD  staticmethod of a decorated class
           - METHOD  method decorated by Require

        *args and **kwargs: The invoke parameters of the decorated method

        For example below is a version getter to get the information from the
        parameter of a method.

        >>> def get_version(decorate_type, *args, **kwargs):
        >>>     version = kwargs.get('version')
        >>>     return version

    1. Decorate a method
    The decorated method will be executed only if the version criteria is
    satisfied, otherwise, `VersionNotSupport` exception is thrown.
    The method overload based on versions is supported with using this
    decorator. User can defined different versions of methods by decorating
    it with different versions criteria. When the method is called, the one
    that satisfying the version will be used.

    Note that the '# noqa' is needed to get rid of pep8 error.

    For example:

    >>>  class Resource1(object):
    >>>
    >>>      @staticmethod
    >>>      @Check('<2.0', get_version)
    >>>      def static_method(version):
    >>>          pass
    >>>
    >>>      @Check('>2.0', get_version)
    >>>      def method(self, version):
    >>>          return '>2.0'
    >>>
    >>>      @Check('<=2.0', get_version)  # noqa
    >>>      def method(self, version):
    >>>          return '<=2.0'

    2. Decorate a class
    The decorated class can not be initiated and its static methods and
    class methods can not be invoked when the version criteria is not
    satisfied.

    For example:

    >>>  @Check('>3.0', get_version)
    >>>  class Resource2(object):
    >>>      def __init__(self, version)
    >>>          super(OneResource, self).__init__()
    >>>          self._version = version
    """

    INIT_METHOD, CLASS_METHOD, INSTANCE_METHOD, STATIC_METHOD, METHOD = range(5)

    def __init__(self, criteria_string, version_getter):
        self.criteria = Criteria.parse(criteria_string)
        self.version_getter = version_getter

    def __call__(self, obj):
        if inspect.isclass(obj):
            return self._cls_decorator(obj)
        else:
            return self._func_decorator(obj)

    def get_version_getter(self):
        return self.version_getter

    def _func_decorator(self, func):
        func_key = VersionedFuncManager.get_function_name(func)
        versioned_func = VersionedFunc(self.criteria, func)
        VersionedFuncManager.add_func(func_key, versioned_func)

        @six.wraps(func)
        def _inner(*args, **kwargs):
            version = self.get_version_getter()(Check.METHOD,
                                                *args, **kwargs)

            inner_func = VersionedFuncManager.get_support_func(
                func_key, version)
            return inner_func(*args, **kwargs)

        return _inner

    def _cls_decorator(self, cls):
        mro_dict = [o.__dict__ for o in inspect.getmro(cls)]
        for attr_name, attr_val in inspect.getmembers(cls):
            if (not inspect.ismethod(attr_val) and
                    not inspect.isfunction(attr_val)):
                # Only handle functions
                continue

            if self._is_classmethod(attr_name, mro_dict):
                setattr(cls, attr_name,
                        self._handle_classmethod(attr_val))

            elif self._is_staticmethod(attr_name, mro_dict):
                setattr(cls, attr_name, self._handle_staticmethod(attr_val))

            elif attr_name == '__init__':
                setattr(cls, attr_name, self._handle_init_method(attr_val))

        return cls

    @staticmethod
    def _is_classmethod(attr_name, mro_dict):
        for mro in mro_dict:
            if attr_name in mro and isinstance(mro[attr_name],
                                               classmethod):
                return True
        return False

    @staticmethod
    def _is_staticmethod(attr_name, mro_dict):
        for mro in mro_dict:
            if attr_name in mro and isinstance(mro[attr_name],
                                               staticmethod):
                return True
        return False

    def _handle_staticmethod(self, func):
        _inner = self._handle_method(Check.STATIC_METHOD, func)
        return staticmethod(_inner)

    def _handle_classmethod(self, func,):
        def _inner(cls, *args, **kwargs):
            self._test_support(Check.CLASS_METHOD,
                               cls, *args, **kwargs)
            return func(*args, **kwargs)
        return classmethod(_inner)

    def _handle_init_method(self, func):
        return self._handle_method(Check.INIT_METHOD, func)

    def _handle_method(self, dec_type, func):
        def _inner(*args, **kwargs):
            self._test_support(dec_type, *args, **kwargs)
            return func(*args, **kwargs)

        return _inner

    def _test_support(self, dec_type, *args, **kwargs):
        version = self.get_version_getter()(dec_type, *args, **kwargs)
        if not self.criteria.test(version):
            raise ex.VersionNotSupport(version=version)
