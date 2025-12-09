import unittest

from aprsd.utils.keepalive_collector import KeepAliveCollector


class MockKeepAliveProducer:
    """Mock implementation of KeepAliveProducer for testing."""

    _instance = None

    def __init__(self, name='MockProducer'):
        self.name = name
        self.check_called = False
        self.log_called = False

    def __call__(self):
        """Make it callable like a singleton."""
        if self._instance is None:
            self._instance = self
        return self._instance

    def keepalive_check(self):
        self.check_called = True

    def keepalive_log(self):
        self.log_called = True


class TestKeepAliveCollector(unittest.TestCase):
    """Unit tests for the KeepAliveCollector class."""

    def setUp(self):
        """Set up test fixtures."""
        # Reset singleton instance
        KeepAliveCollector._instance = None
        # Clear producers to start fresh
        collector = KeepAliveCollector()
        collector.producers = []

    def tearDown(self):
        """Clean up after tests."""
        KeepAliveCollector._instance = None

    def test_singleton_pattern(self):
        """Test that KeepAliveCollector is a singleton."""
        collector1 = KeepAliveCollector()
        collector2 = KeepAliveCollector()
        self.assertIs(collector1, collector2)

    def test_init(self):
        """Test initialization."""
        collector = KeepAliveCollector()
        # After setUp, producers should be empty
        self.assertEqual(len(collector.producers), 0)

    def test_register(self):
        """Test register() method."""
        collector = KeepAliveCollector()
        producer = MockKeepAliveProducer()

        collector.register(producer)
        self.assertIn(producer, collector.producers)

    def test_register_non_protocol(self):
        """Test register() raises TypeError for non-protocol objects."""
        collector = KeepAliveCollector()
        non_producer = object()

        with self.assertRaises(TypeError):
            collector.register(non_producer)

    def test_unregister(self):
        """Test unregister() method."""
        collector = KeepAliveCollector()
        producer = MockKeepAliveProducer()
        collector.register(producer)

        collector.unregister(producer)
        self.assertNotIn(producer, collector.producers)

    def test_unregister_non_protocol(self):
        """Test unregister() raises TypeError for non-protocol objects."""
        collector = KeepAliveCollector()
        non_producer = object()

        with self.assertRaises(TypeError):
            collector.unregister(non_producer)

    def test_check(self):
        """Test check() method."""
        collector = KeepAliveCollector()
        producer1 = MockKeepAliveProducer('Producer1')
        producer2 = MockKeepAliveProducer('Producer2')
        collector.register(producer1)
        collector.register(producer2)

        collector.check()

        self.assertTrue(producer1().check_called)
        self.assertTrue(producer2().check_called)

    def test_check_with_exception(self):
        """Test check() raises exception from producer."""
        collector = KeepAliveCollector()

        class FailingProducer:
            _instance = None

            def __call__(self):
                if self._instance is None:
                    self._instance = self
                return self._instance

            def keepalive_check(self):
                raise RuntimeError('Check error')

            def keepalive_log(self):
                pass

        producer = FailingProducer()
        collector.register(producer)

        with self.assertRaises(RuntimeError):
            collector.check()

    def test_log(self):
        """Test log() method."""
        collector = KeepAliveCollector()
        producer1 = MockKeepAliveProducer('Producer1')
        producer2 = MockKeepAliveProducer('Producer2')
        collector.register(producer1)
        collector.register(producer2)

        collector.log()

        self.assertTrue(producer1().log_called)
        self.assertTrue(producer2().log_called)

    def test_log_with_exception(self):
        """Test log() raises exception from producer."""
        collector = KeepAliveCollector()

        class FailingProducer:
            _instance = None

            def __call__(self):
                if self._instance is None:
                    self._instance = self
                return self._instance

            def keepalive_check(self):
                pass

            def keepalive_log(self):
                raise RuntimeError('Log error')

        producer = FailingProducer()
        collector.register(producer)

        with self.assertRaises(RuntimeError):
            collector.log()

    def test_multiple_producers(self):
        """Test multiple producers are called."""
        collector = KeepAliveCollector()
        call_order = []

        class OrderedProducer:
            _instance = None

            def __init__(self, name):
                self.name = name

            def __call__(self):
                if self._instance is None:
                    self._instance = self
                return self._instance

            def keepalive_check(self):
                call_order.append(self.name)

            def keepalive_log(self):
                pass

        producer1 = OrderedProducer('Producer1')
        producer2 = OrderedProducer('Producer2')
        producer3 = OrderedProducer('Producer3')

        collector.register(producer1)
        collector.register(producer2)
        collector.register(producer3)

        collector.check()

        self.assertEqual(call_order, ['Producer1', 'Producer2', 'Producer3'])

    def test_empty_collector(self):
        """Test check() and log() with no producers."""
        collector = KeepAliveCollector()

        # Should not raise exception
        collector.check()
        collector.log()
