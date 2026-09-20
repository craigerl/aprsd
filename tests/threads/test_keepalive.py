import datetime
import unittest
from unittest import mock

from oslo_config import cfg

from aprsd.threads.keepalive import KeepAliveThread

CONF = cfg.CONF


class TestKeepAliveThread(unittest.TestCase):
    """Unit tests for the KeepAliveThread class."""

    def setUp(self):
        """Set up test fixtures."""
        # Reset the class-level 24h version-check timer so _check_version
        # is never reached in these tests.
        KeepAliveThread.checker_time = datetime.datetime.now()
        CONF.callsign = 'W1AW'

    def _make_thread_with_stats(self, stats_json):
        """Build a KeepAliveThread whose Collector returns the given dict."""
        thread = KeepAliveThread()
        thread.wait = mock.Mock(return_value=False)

        # Minimal stubs for everything loop() touches besides Collector.
        mock_collector = mock.MagicMock()
        mock_collector.collect.return_value = stats_json
        mock_packet_list = mock.MagicMock()
        mock_packet_list.total_rx.return_value = 0
        mock_packet_list.total_tx.return_value = 0
        mock_thread_list = mock.MagicMock()
        mock_thread_list.__len__.return_value = 0
        mock_ka_collector = mock.MagicMock()
        mock_logging_queue = mock.MagicMock()
        mock_logging_queue.qsize.return_value = 0

        patchers = [
            mock.patch(
                'aprsd.threads.keepalive.collector.Collector',
                return_value=mock_collector,
            ),
            mock.patch(
                'aprsd.threads.keepalive.packets.PacketList',
                return_value=mock_packet_list,
            ),
            mock.patch(
                'aprsd.threads.keepalive.APRSDThreadList',
                return_value=mock_thread_list,
            ),
            mock.patch(
                'aprsd.threads.keepalive.keepalive_collector.KeepAliveCollector',
                return_value=mock_ka_collector,
            ),
            mock.patch(
                'aprsd.threads.keepalive.aprsd_log.logging_queue',
                mock_logging_queue,
            ),
        ]
        for p in patchers:
            p.start()
        self.addCleanup(lambda: [p.stop() for p in patchers])

        return thread

    def test_loop_missing_stats_keys_no_crash(self):
        """loop() must not KeyError when a stats producer is missing.

        Collector.collect() swallows producer errors, so a failing
        producer means its key is simply absent from the returned dict.
        loop() previously indexed stats_json['PacketTrack'] and
        stats_json['APRSDStats'] directly, raising KeyError and killing
        the KeepAliveThread (the thread that reports dead threads).
        """
        # No 'PacketTrack' or 'APRSDStats' keys at all.
        thread = self._make_thread_with_stats({})

        result = thread.loop()  # must not raise
        self.assertTrue(result)

    def test_loop_partial_stats_no_crash(self):
        """loop() tolerates a dict missing only some keys."""
        thread = self._make_thread_with_stats(
            {
                'PacketTrack': {'total_tracked': 3},
                # 'APRSDStats' missing entirely
            },
        )

        result = thread.loop()  # must not raise
        self.assertTrue(result)

    def test_loop_full_stats(self):
        """loop() still works with a complete stats dict."""
        thread = self._make_thread_with_stats(
            {
                'APRSDStats': {
                    'callsign': 'W1AW',
                    'uptime': '1 day',
                    'memory_current_str': '10MB',
                    'memory_peak_str': '20MB',
                },
                'PacketTrack': {'total_tracked': 3},
                'PacketList': {
                    'MessagePacket': {'tx': 1, 'rx': 2},
                },
                'APRSDThreadList': {},
            },
        )

        result = thread.loop()
        self.assertTrue(result)
