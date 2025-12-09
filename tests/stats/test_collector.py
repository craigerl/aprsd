import unittest
from unittest import mock

from aprsd.stats import collector


class MockStatsProducer:
    """Mock implementation of StatsProducer for testing."""

    _instance = None

    def __init__(self, name='MockProducer'):
        self.name = name
        self.stats_called = False

    def __call__(self):
        """Make it callable like a singleton."""
        if self._instance is None:
            self._instance = self
        return self._instance

    def stats(self, serializable=False):
        self.stats_called = True
        return {'test': 'data', 'serializable': serializable}


class TestStatsCollector(unittest.TestCase):
    """Unit tests for the Collector class."""

    def setUp(self):
        """Set up test fixtures."""
        # Reset singleton instance
        collector.Collector._instance = None
        # Clear producers to start fresh
        c = collector.Collector()
        c.producers = []

    def tearDown(self):
        """Clean up after tests."""
        collector.Collector._instance = None

    def test_singleton_pattern(self):
        """Test that Collector is a singleton."""
        collector1 = collector.Collector()
        collector2 = collector.Collector()
        self.assertIs(collector1, collector2)

    def test_init(self):
        """Test initialization."""
        c = collector.Collector()
        # After setUp, producers should be empty
        self.assertEqual(len(c.producers), 0)

    def test_register_producer(self):
        """Test register_producer() method."""
        c = collector.Collector()
        producer = MockStatsProducer()

        c.register_producer(producer)
        self.assertIn(producer, c.producers)

    def test_register_producer_non_protocol(self):
        """Test register_producer() raises TypeError for non-protocol objects."""
        c = collector.Collector()
        non_producer = object()

        with self.assertRaises(TypeError):
            c.register_producer(non_producer)

    def test_unregister_producer(self):
        """Test unregister_producer() method."""
        c = collector.Collector()
        producer = MockStatsProducer()
        c.register_producer(producer)

        c.unregister_producer(producer)
        self.assertNotIn(producer, c.producers)

    def test_unregister_producer_non_protocol(self):
        """Test unregister_producer() raises TypeError for non-protocol objects."""
        c = collector.Collector()
        non_producer = object()

        with self.assertRaises(TypeError):
            c.unregister_producer(non_producer)

    def test_collect(self):
        """Test collect() method."""
        c = collector.Collector()
        producer1 = MockStatsProducer('Producer1')
        producer2 = MockStatsProducer('Producer2')
        c.register_producer(producer1)
        c.register_producer(producer2)

        stats = c.collect()

        self.assertIsInstance(stats, dict)
        self.assertIn('MockStatsProducer', stats)
        self.assertTrue(producer1().stats_called)
        self.assertTrue(producer2().stats_called)

    def test_collect_serializable(self):
        """Test collect() with serializable=True."""
        c = collector.Collector()
        producer = MockStatsProducer()
        c.register_producer(producer)

        stats = c.collect(serializable=True)
        # Should pass serializable flag to producers
        self.assertIsInstance(stats, dict)

    def test_collect_with_exception(self):
        """Test collect() raises exception from producer."""
        c = collector.Collector()

        class FailingProducer:
            _instance = None

            def __call__(self):
                if self._instance is None:
                    self._instance = self
                return self._instance

            def stats(self, serializable=False):
                raise RuntimeError('Stats error')

        producer = FailingProducer()
        c.register_producer(producer)

        with self.assertRaises(RuntimeError):
            c.collect()

    def test_stop_all(self):
        """Test stop_all() method."""
        c = collector.Collector()
        producer1 = MockStatsProducer('Producer1')
        producer2 = MockStatsProducer('Producer2')
        c.register_producer(producer1)
        c.register_producer(producer2)

        with mock.patch('aprsd.stats.collector.LOG') as mock_log:
            c.stop_all()

            self.assertEqual(len(c.producers), 0)
            # Should log for each producer
            self.assertGreaterEqual(mock_log.info.call_count, 2)

    def test_multiple_producers(self):
        """Test multiple producers are collected."""
        c = collector.Collector()
        call_order = []

        class OrderedProducer:
            _instance = None

            def __init__(self, name):
                self.name = name

            def __call__(self):
                if self._instance is None:
                    self._instance = self
                return self._instance

            def stats(self, serializable=False):
                call_order.append(self.name)
                return {'name': self.name}

        producer1 = OrderedProducer('Producer1')
        producer2 = OrderedProducer('Producer2')
        producer3 = OrderedProducer('Producer3')

        c.register_producer(producer1)
        c.register_producer(producer2)
        c.register_producer(producer3)

        stats = c.collect()

        # All producers are called (verified by call_order)
        self.assertIn('Producer1', call_order)
        self.assertIn('Producer2', call_order)
        self.assertIn('Producer3', call_order)
        # But stats dict only has 1 entry because all have same class name
        # (last one overwrites previous ones)
        self.assertEqual(len(stats), 1)
        self.assertIn('OrderedProducer', stats)

    def test_empty_collector(self):
        """Test collect() with no producers."""
        c = collector.Collector()
        stats = c.collect()
        self.assertEqual(stats, {})
