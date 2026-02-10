import unittest
from unittest import mock

import requests

from aprsd.stats import collector
from aprsd.threads.stats import (
    APRSDPushStatsThread,
    APRSDStatsStoreThread,
    StatsStore,
)


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
            mock_collector_instance.collect.side_effect = RuntimeError('Test exception')
            mock_collector_class.return_value = mock_collector_instance

            # Set loop_count to match save interval
            thread.loop_count = 10

            # Should raise the exception
            with self.assertRaises(RuntimeError):
                thread.loop()

    # Removed test_loop_count_increment as it's not meaningful to test in isolation
    # since the increment happens in the parent run() method, not in loop()


class TestAPRSDPushStatsThread(unittest.TestCase):
    """Unit tests for the APRSDPushStatsThread class."""

    def test_init_with_explicit_args(self):
        """Test initialization with explicit push_url, frequency, and send_packetlist."""
        thread = APRSDPushStatsThread(
            push_url='https://example.com/api',
            frequency_seconds=30,
            send_packetlist=True,
        )
        self.assertEqual(thread.name, 'PushStats')
        self.assertEqual(thread.push_url, 'https://example.com/api')
        self.assertEqual(thread.period, 30)
        self.assertTrue(thread.send_packetlist)
        self.assertTrue(hasattr(thread, 'loop_count'))

    def test_init_uses_conf_when_args_not_passed(self):
        """Test initialization uses CONF.push_stats when args omitted."""
        with mock.patch('aprsd.threads.stats.CONF') as mock_conf:
            mock_conf.push_stats.push_url = 'https://conf.example.com'
            mock_conf.push_stats.frequency_seconds = 15
            thread = APRSDPushStatsThread()
            self.assertEqual(thread.push_url, 'https://conf.example.com')
            self.assertEqual(thread.period, 15)
            self.assertFalse(thread.send_packetlist)

    def test_loop_skips_push_when_period_not_reached(self):
        """Test loop does not POST when loop_count not divisible by period."""
        thread = APRSDPushStatsThread(
            push_url='https://example.com',
            frequency_seconds=10,
        )
        thread.loop_count = 3  # 3 % 10 != 0

        with (
            mock.patch('aprsd.threads.stats.collector.Collector') as mock_collector,
            mock.patch('aprsd.threads.stats.requests.post') as mock_post,
            mock.patch('aprsd.threads.stats.time.sleep'),
        ):
            result = thread.loop()

        self.assertTrue(result)
        mock_collector.return_value.collect.assert_not_called()
        mock_post.assert_not_called()

    def test_loop_pushes_stats_and_removes_packetlist_by_default(self):
        """Test loop collects stats, POSTs to url/stats, and strips PacketList.packets."""
        thread = APRSDPushStatsThread(
            push_url='https://example.com',
            frequency_seconds=10,
            send_packetlist=False,
        )
        thread.loop_count = 10

        collected = {
            'PacketList': {'packets': [1, 2, 3], 'rx': 5, 'tx': 1},
            'Other': 'data',
        }

        with (
            mock.patch(
                'aprsd.threads.stats.collector.Collector'
            ) as mock_collector_class,
            mock.patch('aprsd.threads.stats.requests.post') as mock_post,
            mock.patch('aprsd.threads.stats.time.sleep'),
            mock.patch('aprsd.threads.stats.datetime') as mock_dt,
        ):
            mock_collector_class.return_value.collect.return_value = collected
            mock_dt.datetime.now.return_value.strftime.return_value = (
                '01-01-2025 12:00:00'
            )

            result = thread.loop()

        self.assertTrue(result)
        mock_collector_class.return_value.collect.assert_called_once_with(
            serializable=True
        )
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        self.assertEqual(call_args[0][0], 'https://example.com/stats')
        self.assertEqual(call_args[1]['headers'], {'Content-Type': 'application/json'})
        self.assertEqual(call_args[1]['timeout'], 5)
        body = call_args[1]['json']
        self.assertEqual(body['time'], '01-01-2025 12:00:00')
        self.assertNotIn('packets', body['stats']['PacketList'])
        self.assertEqual(body['stats']['PacketList']['rx'], 5)
        self.assertEqual(body['stats']['Other'], 'data')

    def test_loop_pushes_stats_with_packetlist_when_send_packetlist_true(self):
        """Test loop includes PacketList.packets when send_packetlist is True."""
        thread = APRSDPushStatsThread(
            push_url='https://example.com',
            frequency_seconds=10,
            send_packetlist=True,
        )
        thread.loop_count = 10

        collected = {'PacketList': {'packets': [1, 2, 3], 'rx': 5}}

        with (
            mock.patch(
                'aprsd.threads.stats.collector.Collector'
            ) as mock_collector_class,
            mock.patch('aprsd.threads.stats.requests.post') as mock_post,
            mock.patch('aprsd.threads.stats.time.sleep'),
            mock.patch('aprsd.threads.stats.datetime') as mock_dt,
        ):
            mock_collector_class.return_value.collect.return_value = collected
            mock_dt.datetime.now.return_value.strftime.return_value = (
                '01-01-2025 12:00:00'
            )

            result = thread.loop()

        self.assertTrue(result)
        body = mock_post.call_args[1]['json']
        self.assertEqual(body['stats']['PacketList']['packets'], [1, 2, 3])

    def test_loop_on_http_200_logs_success(self):
        """Test loop logs info on successful 200 response."""
        thread = APRSDPushStatsThread(
            push_url='https://example.com',
            frequency_seconds=10,
        )
        thread.loop_count = 10

        with (
            mock.patch(
                'aprsd.threads.stats.collector.Collector'
            ) as mock_collector_class,
            mock.patch('aprsd.threads.stats.requests.post') as mock_post,
            mock.patch('aprsd.threads.stats.time.sleep'),
            mock.patch('aprsd.threads.stats.datetime') as mock_dt,
            mock.patch('aprsd.threads.stats.LOGU') as mock_logu,
        ):
            mock_collector_class.return_value.collect.return_value = {}
            mock_dt.datetime.now.return_value.strftime.return_value = (
                '01-01-2025 12:00:00'
            )
            mock_post.return_value.status_code = 200
            mock_post.return_value.raise_for_status = mock.Mock()

            result = thread.loop()

        self.assertTrue(result)
        mock_logu.info.assert_called()
        self.assertIn('Successfully pushed stats', mock_logu.info.call_args[0][0])

    def test_loop_on_non_200_logs_warning(self):
        """Test loop logs warning when response is not 200."""
        thread = APRSDPushStatsThread(
            push_url='https://example.com',
            frequency_seconds=10,
        )
        thread.loop_count = 10

        with (
            mock.patch(
                'aprsd.threads.stats.collector.Collector'
            ) as mock_collector_class,
            mock.patch('aprsd.threads.stats.requests.post') as mock_post,
            mock.patch('aprsd.threads.stats.time.sleep'),
            mock.patch('aprsd.threads.stats.datetime') as mock_dt,
            mock.patch('aprsd.threads.stats.LOGU') as mock_logu,
        ):
            mock_collector_class.return_value.collect.return_value = {}
            mock_dt.datetime.now.return_value.strftime.return_value = (
                '01-01-2025 12:00:00'
            )
            mock_post.return_value.status_code = 500
            mock_post.return_value.raise_for_status = mock.Mock()

            result = thread.loop()

        self.assertTrue(result)
        mock_logu.warning.assert_called_once()
        self.assertIn('Failed to push stats', mock_logu.warning.call_args[0][0])
        self.assertIn('500', mock_logu.warning.call_args[0][0])

    def test_loop_on_request_exception_logs_error_and_continues(self):
        """Test loop logs error on requests.RequestException and returns True."""
        thread = APRSDPushStatsThread(
            push_url='https://example.com',
            frequency_seconds=10,
        )
        thread.loop_count = 10

        with (
            mock.patch(
                'aprsd.threads.stats.collector.Collector'
            ) as mock_collector_class,
            mock.patch('aprsd.threads.stats.requests.post') as mock_post,
            mock.patch('aprsd.threads.stats.time.sleep'),
            mock.patch('aprsd.threads.stats.datetime') as mock_dt,
            mock.patch('aprsd.threads.stats.LOGU') as mock_logu,
        ):
            mock_collector_class.return_value.collect.return_value = {}
            mock_dt.datetime.now.return_value.strftime.return_value = (
                '01-01-2025 12:00:00'
            )
            mock_post.side_effect = requests.exceptions.ConnectionError(
                'Connection refused'
            )

            result = thread.loop()

        self.assertTrue(result)
        mock_logu.error.assert_called_once()
        self.assertIn('Error pushing stats', mock_logu.error.call_args[0][0])

    def test_loop_on_other_exception_logs_error_and_continues(self):
        """Test loop logs error on unexpected exception and returns True."""
        thread = APRSDPushStatsThread(
            push_url='https://example.com',
            frequency_seconds=10,
        )
        thread.loop_count = 10

        with (
            mock.patch(
                'aprsd.threads.stats.collector.Collector'
            ) as mock_collector_class,
            mock.patch('aprsd.threads.stats.requests.post') as mock_post,
            mock.patch('aprsd.threads.stats.time.sleep'),
            mock.patch('aprsd.threads.stats.datetime') as mock_dt,
            mock.patch('aprsd.threads.stats.LOGU') as mock_logu,
        ):
            mock_collector_class.return_value.collect.return_value = {}
            mock_dt.datetime.now.return_value.strftime.return_value = (
                '01-01-2025 12:00:00'
            )
            mock_post.side_effect = ValueError('unexpected')

            result = thread.loop()

        self.assertTrue(result)
        mock_logu.error.assert_called_once()
        self.assertIn('Unexpected error in stats push', mock_logu.error.call_args[0][0])

    def test_loop_no_packetlist_key_in_stats(self):
        """Test loop does not fail when stats have no PacketList key."""
        thread = APRSDPushStatsThread(
            push_url='https://example.com',
            frequency_seconds=10,
            send_packetlist=False,
        )
        thread.loop_count = 10

        collected = {'Only': 'data', 'No': 'PacketList'}

        with (
            mock.patch(
                'aprsd.threads.stats.collector.Collector'
            ) as mock_collector_class,
            mock.patch('aprsd.threads.stats.requests.post') as mock_post,
            mock.patch('aprsd.threads.stats.time.sleep'),
            mock.patch('aprsd.threads.stats.datetime') as mock_dt,
        ):
            mock_collector_class.return_value.collect.return_value = collected
            mock_dt.datetime.now.return_value.strftime.return_value = (
                '01-01-2025 12:00:00'
            )

            result = thread.loop()

        self.assertTrue(result)
        body = mock_post.call_args[1]['json']
        self.assertEqual(body['stats'], collected)


if __name__ == '__main__':
    unittest.main()
