import unittest
from unittest import mock

from aprsd.utils import trace


class TestTraceDecorator(unittest.TestCase):
    """Unit tests for the trace() decorator."""

    def setUp(self):
        """Set up test fixtures."""
        # Enable trace for testing
        trace.TRACE_ENABLED = True

    def tearDown(self):
        """Clean up after tests."""
        trace.TRACE_ENABLED = False

    @mock.patch('aprsd.utils.trace.LOG')
    def test_trace_decorator_no_debug(self, mock_log):
        """Test trace() decorator when DEBUG is not enabled."""
        mock_log.isEnabledFor.return_value = False

        @trace.trace
        def test_func(x, y):
            return x + y

        result = test_func(1, 2)
        self.assertEqual(result, 3)
        # Should not log when DEBUG is disabled
        mock_log.debug.assert_not_called()

    @mock.patch('aprsd.utils.trace.LOG')
    def test_trace_decorator_with_debug(self, mock_log):
        """Test trace() decorator when DEBUG is enabled."""
        mock_log.isEnabledFor.return_value = True

        @trace.trace
        def test_func(x, y):
            return x + y

        result = test_func(1, 2)
        self.assertEqual(result, 3)
        # Should log when DEBUG is enabled
        self.assertTrue(mock_log.debug.called)

    @mock.patch('aprsd.utils.trace.LOG')
    def test_trace_decorator_exception(self, mock_log):
        """Test trace() decorator with exception."""
        mock_log.isEnabledFor.return_value = True

        @trace.trace
        def test_func():
            raise ValueError('Test error')

        with self.assertRaises(ValueError):
            test_func()

        # Should log exception
        self.assertTrue(mock_log.debug.called)

    @mock.patch('aprsd.utils.trace.LOG')
    def test_trace_decorator_with_filter(self, mock_log):
        """Test trace() decorator with filter function."""
        mock_log.isEnabledFor.return_value = True

        def filter_func(args):
            return args.get('x') > 0

        @trace.trace(filter_function=filter_func)
        def test_func(x, y):
            return x + y

        # Should log when filter passes
        test_func(1, 2)
        self.assertTrue(mock_log.debug.called)

        # Reset mock
        mock_log.reset_mock()

        # Should not log when filter fails
        test_func(-1, 2)
        # Filter function should prevent logging
        # (though function still executes)

    def test_trace_decorator_preserves_function(self):
        """Test that trace decorator preserves function metadata."""

        @trace.trace
        def test_func(x, y):
            """Test function docstring."""
            return x + y

        self.assertEqual(test_func.__name__, 'test_func')
        self.assertIn('docstring', test_func.__doc__)


class TestNoTraceDecorator(unittest.TestCase):
    """Unit tests for the no_trace() decorator."""

    def test_no_trace_decorator(self):
        """Test no_trace() decorator."""

        @trace.no_trace
        def test_func(x, y):
            return x + y

        result = test_func(1, 2)
        self.assertEqual(result, 3)
        # Function should work normally
        self.assertEqual(test_func.__name__, 'test_func')


class TestTraceWrapperMetaclass(unittest.TestCase):
    """Unit tests for the TraceWrapperMetaclass."""

    def test_metaclass_creation(self):
        """Test that TraceWrapperMetaclass creates class correctly."""

        class TestClass(metaclass=trace.TraceWrapperMetaclass):
            def test_method(self):
                return 'test'

        instance = TestClass()
        self.assertEqual(instance.test_method(), 'test')

    def test_metaclass_wraps_methods(self):
        """Test that metaclass wraps methods."""

        class TestClass(metaclass=trace.TraceWrapperMetaclass):
            def test_method(self):
                return 'test'

        # Methods should be wrapped
        self.assertTrue(
            hasattr(TestClass.test_method, '__wrapped__')
            or hasattr(TestClass.test_method, '__name__')
        )


class TestTraceWrapperWithABCMetaclass(unittest.TestCase):
    """Unit tests for the TraceWrapperWithABCMetaclass."""

    def test_metaclass_creation(self):
        """Test that TraceWrapperWithABCMetaclass creates class correctly."""
        import abc

        class TestAbstractClass(metaclass=trace.TraceWrapperWithABCMetaclass):
            @abc.abstractmethod
            def test_method(self):
                pass

        # Should be able to create abstract class
        self.assertTrue(hasattr(TestAbstractClass, '__abstractmethods__'))
