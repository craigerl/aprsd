import datetime
import unittest
from unittest import mock

from oslo_config import cfg

from aprsd.stats import app

CONF = cfg.CONF


class TestAPRSDStats(unittest.TestCase):
    """Unit tests for the APRSDStats class."""

    def setUp(self):
        """Set up test fixtures."""
        # Reset singleton instance
        app.APRSDStats._instance = None
        CONF.callsign = 'TEST'

    def tearDown(self):
        """Clean up after tests."""
        app.APRSDStats._instance = None

    def test_singleton_pattern(self):
        """Test that APRSDStats is a singleton."""
        stats1 = app.APRSDStats()
        stats2 = app.APRSDStats()
        self.assertIs(stats1, stats2)

    def test_init(self):
        """Test initialization."""
        stats = app.APRSDStats()
        self.assertIsNotNone(stats.start_time)
        self.assertIsInstance(stats.start_time, datetime.datetime)

    def test_uptime(self):
        """Test uptime() method."""
        stats = app.APRSDStats()
        import time

        time.sleep(0.1)  # Small delay

        uptime = stats.uptime()
        self.assertIsInstance(uptime, datetime.timedelta)
        self.assertGreaterEqual(uptime.total_seconds(), 0.1)

    @mock.patch('aprsd.stats.app.tracemalloc.get_traced_memory')
    @mock.patch('aprsd.stats.app.aprsd_log.logging_queue')
    def test_stats(self, mock_queue, mock_tracemalloc):
        """Test stats() method."""
        mock_tracemalloc.return_value = (1024 * 1024, 2 * 1024 * 1024)  # 1MB, 2MB
        mock_queue.qsize.return_value = 5

        stats = app.APRSDStats()
        result = stats.stats()

        self.assertIn('version', result)
        self.assertIn('uptime', result)
        self.assertIn('callsign', result)
        self.assertIn('memory_current', result)
        self.assertIn('memory_current_str', result)
        self.assertIn('memory_peak', result)
        self.assertIn('memory_peak_str', result)
        self.assertIn('loging_queue', result)
        self.assertEqual(result['callsign'], 'TEST')
        self.assertEqual(result['memory_current'], 1024 * 1024)
        self.assertEqual(result['loging_queue'], 5)

    @mock.patch('aprsd.stats.app.tracemalloc.get_traced_memory')
    @mock.patch('aprsd.stats.app.aprsd_log.logging_queue')
    def test_stats_serializable(self, mock_queue, mock_tracemalloc):
        """Test stats() with serializable=True."""
        mock_tracemalloc.return_value = (1024 * 1024, 2 * 1024 * 1024)
        mock_queue.qsize.return_value = 5

        stats = app.APRSDStats()
        result = stats.stats(serializable=True)

        self.assertIsInstance(result['uptime'], str)
        # Should be JSON serializable
        import json

        json.dumps(result)  # Should not raise exception

    def test_stats_memory_formatting(self):
        """Test that memory is formatted correctly."""
        with mock.patch(
            'aprsd.stats.app.tracemalloc.get_traced_memory'
        ) as mock_tracemalloc:
            with mock.patch('aprsd.stats.app.aprsd_log.logging_queue') as mock_queue:
                mock_tracemalloc.return_value = (1024 * 1024, 2 * 1024 * 1024)
                mock_queue.qsize.return_value = 0

                stats = app.APRSDStats()
                result = stats.stats()

                # 1MB should format as 'MB', not 'KB'
                self.assertIn('MB', result['memory_current_str'])
                self.assertIn('MB', result['memory_peak_str'])
