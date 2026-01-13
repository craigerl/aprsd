import unittest
from unittest import mock

from aprsd.stats import collector
from aprsd.threads.stats import APRSDStatsStoreThread, StatsStore


class TestStatsStore(unittest.TestCase):
    """Unit tests for the StatsStore class."""

    def test_init(self):
        """Test StatsStore initialization."""
        ss = StatsStore()
        self.assertIsNotNone(ss.lock)
        self.assertFalse(hasattr(ss, 'data'))

    def test_add(self):
        """Test add method."""
        ss = StatsStore()
        test_data = {'test': 'data'}

        ss.add(test_data)
        self.assertEqual(ss.data, test_data)

    def test_add_concurrent(self):
        """Test add method with concurrent access."""
        import threading

        ss = StatsStore()
        test_data = {'test': 'data'}
        results = []

        def add_data():
            ss.add(test_data)
            results.append(ss.data)

        # Create multiple threads to test thread safety
        threads = []
        for _ in range(5):
            t = threading.Thread(target=add_data)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # All threads should have added the data
        for result in results:
            self.assertEqual(result, test_data)


class TestAPRSDStatsStoreThread(unittest.TestCase):
    """Unit tests for the APRSDStatsStoreThread class."""

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

    def test_init(self):
        """Test APRSDStatsStoreThread initialization."""
        thread = APRSDStatsStoreThread()
        self.assertEqual(thread.name, 'StatsStore')
        self.assertEqual(thread.save_interval, 10)
        self.assertTrue(hasattr(thread, 'loop_count'))

    def test_loop_with_save(self):
        """Test loop method when save interval is reached."""
        thread = APRSDStatsStoreThread()

        # Mock the collector and save methods
        with (
            mock.patch('aprsd.stats.collector.Collector') as mock_collector_class,
            mock.patch('aprsd.utils.objectstore.ObjectStoreMixin.save') as mock_save,
        ):
            # Setup mock collector to return some stats
            mock_collector_instance = mock.Mock()
            mock_collector_instance.collect.return_value = {'test': 'data'}
            mock_collector_class.return_value = mock_collector_instance

            # Set loop_count to match save interval
            thread.loop_count = 10

            # Call loop
            result = thread.loop()

            # Should return True (continue looping)
            self.assertTrue(result)

            # Should have called collect and save
            mock_collector_instance.collect.assert_called_once()
            mock_save.assert_called_once()

    def test_loop_without_save(self):
        """Test loop method when save interval is not reached."""
        thread = APRSDStatsStoreThread()

        # Mock the collector and save methods
        with (
            mock.patch('aprsd.stats.collector.Collector') as mock_collector_class,
            mock.patch('aprsd.utils.objectstore.ObjectStoreMixin.save') as mock_save,
        ):
            # Setup mock collector to return some stats
            mock_collector_instance = mock.Mock()
            mock_collector_instance.collect.return_value = {'test': 'data'}
            mock_collector_class.return_value = mock_collector_instance

            # Set loop_count to not match save interval
            thread.loop_count = 1

            # Call loop
            result = thread.loop()

            # Should return True (continue looping)
            self.assertTrue(result)

            # Should not have called save
            mock_save.assert_not_called()

    def test_loop_with_exception(self):
        """Test loop method when an exception occurs."""
        thread = APRSDStatsStoreThread()

        # Mock the collector to raise an exception
        with mock.patch('aprsd.stats.collector.Collector') as mock_collector_class:
            mock_collector_instance = mock.Mock()
            mock_collector_instance.collect.side_effect = Exception('Test exception')
            mock_collector_class.return_value = mock_collector_instance

            # Set loop_count to match save interval
            thread.loop_count = 10

            # Should raise the exception
            with self.assertRaises(Exception):
                thread.loop()

    # Removed test_loop_count_increment as it's not meaningful to test in isolation
    # since the increment happens in the parent run() method, not in loop()


if __name__ == '__main__':
    unittest.main()
