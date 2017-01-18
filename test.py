from unittest import TestCase

import ddt
from hamcrest import assert_that, equal_to, raises
import mock
import six

from versioncheck import version_check, Check
from versioncheck.check import Criteria
import versioncheck.exceptions as ex


def fake_get_version(dec_type, *args, **kwargs):
    """Fake version getter for unit test.

    This will not be used because it will be patched
    """
    return None


def require_version(criteria):
    return version_check(criteria, fake_get_version)


class Parent(object):
    @classmethod
    def parent_cls_method(cls, o):
        return o

    @staticmethod
    def parent_static_method(o, m=None):
        return o, m

    def parent_method(self, o):
        return o


@require_version('>2')
class DemoChild1(Parent):
    def __init__(self, a):
        self.attr1 = a

    @classmethod
    def cls_method(cls, o):
        return o

    @staticmethod
    def static_method(o):
        return o

    def method(self, o):
        return o


def patch_version_getter(version=None):

    def _inner(func):
        fake_getter = mock.Mock(return_value=version)
        mocked_func = mock.patch.object(version_check, 'get_version_getter',
                                        mock.Mock(return_value=fake_getter))(func)

        @six.wraps(func)
        def _do(*args, **kwargs):
            args = args + (fake_getter,)
            return mocked_func(*args, **kwargs)
        return _do
    return _inner


class VersionCheckDecorateClassTest(TestCase):
    @patch_version_getter('4')
    def test_cls_method_in_parent_support(self, fake_getter):
        assert_that(DemoChild1.parent_cls_method(4), equal_to(4))
        fake_getter.assert_called_with(Check.CLASS_METHOD, DemoChild1, 4)

    @patch_version_getter('2')
    def test_cls_method_in_parent_unsupport(self, _):
        def do():
            DemoChild1.parent_cls_method(None)
        assert_that(do, raises(ex.VersionNotSupport))

    @patch_version_getter('4')
    def test_static_method_in_parent_support(self, fake_getter):
        assert_that(DemoChild1.parent_static_method('a', m='b'),
                    equal_to(('a', 'b')))
        fake_getter.assert_called_with(Check.STATIC_METHOD, 'a', m='b')

    @patch_version_getter('1')
    def test_static_method_in_parent_unsupport(self, _):
        def do():
            DemoChild1.parent_static_method(None)
        assert_that(do, raises(ex.VersionNotSupport))

    @patch_version_getter('4')
    def test_cls_method_support(self, fake_getter):
        assert_that(DemoChild1.cls_method('a'), equal_to('a'))
        fake_getter.assert_called_with(Check.CLASS_METHOD, DemoChild1, 'a')

    @patch_version_getter('1')
    def test_cls_method_unsupport(self, _):
        def do():
            DemoChild1.cls_method('a')
        assert_that(do, raises(ex.VersionNotSupport))

    @patch_version_getter('4')
    def test_static_method_support(self, fake_getter):
        assert_that(DemoChild1.static_method('b'), equal_to('b'))
        fake_getter.assert_called_with(Check.STATIC_METHOD, 'b')

    @patch_version_getter('1')
    def test_static_method_unsupport(self, _):
        def do():
            DemoChild1.static_method('a')
        assert_that(do, raises(ex.VersionNotSupport))

    @patch_version_getter(None)
    def test_new_instance_support(self, fake_getter):
        o = DemoChild1('b')
        assert_that(o.attr1, equal_to('b'))
        fake_getter.assert_called_with(Check.INIT_METHOD, o, 'b')

    @patch_version_getter('2')
    def test_new_instance_unsupport(self, _):
        def do():
            DemoChild1.static_method('a')
        assert_that(do, raises(ex.VersionNotSupport))


class DemoChild2(Parent):
    @classmethod
    @require_version('>2')
    def cls_method(cls, o):
        return o

    @staticmethod
    @require_version('>2')
    def static_method(o):
        return o

    @require_version('>2')
    def method(self):
        return True

    @require_version('>2')
    def versioned_method(self):
        return '>2'

    @require_version('<2')  # noqa
    def versioned_method(self):
        return '<2'


class VersionCheckDecorateMethodTest(TestCase):
    @patch_version_getter('3')
    def test_decorate_method(self, fake_getter):
        o = DemoChild2()
        assert_that(o.method(), equal_to(True))
        fake_getter.assert_called_with(Check.METHOD, o)

    @patch_version_getter('3')
    def test_decorate_cls_method_support(self, fake_getter):
        o = DemoChild2()
        assert_that(o.cls_method('a'), equal_to('a'))
        fake_getter.assert_called_with(Check.METHOD, DemoChild2, 'a')

    @patch_version_getter('3')
    def test_decorate_static_method_support(self, fake_getter):
        o = DemoChild2()
        assert_that(o.static_method('b'), equal_to('b'))
        fake_getter.assert_called_with(Check.METHOD, 'b')

    @patch_version_getter()
    def test_versioned_method(self, fake_getter):
        res = DemoChild2()
        fake_getter.return_value = '3'
        re = res.versioned_method()
        assert_that(re, equal_to('>2'))
        fake_getter.return_value = '1'
        re = res.versioned_method()
        assert_that(re, equal_to('<2'))
        fake_getter.return_value = '2'
        assert_that(res.versioned_method, raises(ex.VersionNotSupport))


@ddt.ddt
class CriteriaTest(TestCase):
    @ddt.data(('5.0.1', '>5.0', True),
              (None, '>5.0', True),
              ('1.0', '>=1.0', True),
              ('1.0.1', '>=1.0', True),
              ('2.0.2.1', '<2.0.3', True),
              ('2.1.a', '<2.0.3', False),
              ('2.0.3', '<=2.0.3', True),
              ('2.1.a', '<=2.0.3', False),
              ('5.0', '=5.0', True),
              ('5.0', '==5.0', True),
              ('5.0.1', '= 5.0', False),
              ('5.0.1', '!= 5.0', True),
              ('5.0', '!=5.0', False),
              ('2.1.0.2', '2.0.5<>4.0.3', True),
              ('4.0.3.1', '2.0.5<>4.0.3', False),
              ('5.0.1', '2.0.5<>4.0.3', False))
    @ddt.unpack
    def test_criteria_test(self, version, criteria, result):
        criteria = Criteria.parse(criteria)
        assert_that(criteria.test(version), equal_to(result))
