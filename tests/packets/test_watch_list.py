import datetime
import unittest

from oslo_config import cfg

from aprsd.packets import watch_list
from tests import fake

CONF = cfg.CONF


class TestWatchList(unittest.TestCase):
    """Unit tests for the WatchList class."""

    def setUp(self):
        """Set up test fixtures."""
        # Reset singleton AND class-level state fully between tests
        watch_list.WatchList._instance = None
        watch_list.WatchList.data = {}
        watch_list.WatchList.initialized = False
        # Mock config
        CONF.watch_list.enabled = True
        CONF.watch_list.callsigns = ['TEST*']
        CONF.watch_list.alert_time_seconds = 300

    def tearDown(self):
        """Clean up after tests."""
        watch_list.WatchList._instance = None
        watch_list.WatchList.data = {}
        watch_list.WatchList.initialized = False

    def test_singleton_pattern(self):
        """Test that WatchList is a singleton."""
        wl1 = watch_list.WatchList()
        wl2 = watch_list.WatchList()
        self.assertIs(wl1, wl2)

    def test_init(self):
        """Test initialization."""
        wl = watch_list.WatchList()
        self.assertIsInstance(wl.data, dict)

    def test_update_from_conf(self):
        """Test _update_from_conf() method."""
        CONF.watch_list.enabled = True
        CONF.watch_list.callsigns = ['TEST1*', 'TEST2*']
        watch_list.WatchList._instance = None

        wl = watch_list.WatchList()
        # Should have entries for TEST1 and TEST2 (without *)
        self.assertIn('TEST1', wl.data)
        self.assertIn('TEST2', wl.data)

    def test_stats_empty(self):
        """stats() returns an empty dict when the watch list is empty."""
        watch_list.WatchList._instance = None
        CONF.watch_list.callsigns = []
        wl = watch_list.WatchList()
        self.assertEqual(wl.stats(), {})

    def test_stats_returns_enriched_shape(self):
        """stats() must return the enriched dict shape, not the raw internal data.

        Regression test for the early-return bug: 'return self.data' was the
        first statement in stats(), bypassing the lock and returning the raw
        internal dict instead of the expected {callsign: {last, packet, age, old}}
        shape that callers rely on.
        """
        watch_list.WatchList._instance = None
        CONF.watch_list.callsigns = ['ENRICHED*']
        wl = watch_list.WatchList()

        # Populate with a seen packet so there is something to report
        from tests import fake

        packet = fake.fake_packet(fromcall='ENRICHED')
        wl.rx(packet)

        stats = wl.stats()

        self.assertIn('ENRICHED', stats)
        entry = stats['ENRICHED']
        # These keys are built by the locked loop — absent if early return fires
        self.assertIn('last', entry)
        self.assertIn('packet', entry)
        self.assertIn('age', entry)
        self.assertIn('old', entry)
        # Confirm we are NOT getting the raw internal key that only exists there
        self.assertNotIn('was_old_before_update', entry)

    def test_stats_not_raw_internal_dict(self):
        """stats() must not return the raw self.data reference.

        If stats() returns self.data directly, mutations via rx() after the
        call would silently alter the returned value — and any consumer
        that sees 'was_old_before_update' knows it got the raw dict.
        """
        watch_list.WatchList._instance = None
        CONF.watch_list.callsigns = ['RAW*']
        wl = watch_list.WatchList()

        stats = wl.stats()
        # stats() should return a freshly-built dict, not the live self.data ref
        self.assertIsNot(stats, wl.data)

    def test_stats(self):
        """Test stats() method."""
        wl = watch_list.WatchList()
        stats = wl.stats()
        self.assertIsInstance(stats, dict)

        stats_serializable = wl.stats(serializable=True)
        self.assertIsInstance(stats_serializable, dict)

    def test_is_enabled(self):
        """Test is_enabled() method."""
        wl = watch_list.WatchList()
        CONF.watch_list.enabled = True
        self.assertTrue(wl.is_enabled())

        CONF.watch_list.enabled = False
        self.assertFalse(wl.is_enabled())

    def test_callsign_in_watchlist(self):
        """Test callsign_in_watchlist() method."""
        wl = watch_list.WatchList()
        CONF.watch_list.callsigns = ['TEST1*']
        watch_list.WatchList._instance = None
        wl = watch_list.WatchList()

        self.assertTrue(wl.callsign_in_watchlist('TEST1'))
        self.assertFalse(wl.callsign_in_watchlist('NOTINLIST'))

    def test_rx(self):
        """Test rx() method."""
        wl = watch_list.WatchList()
        CONF.watch_list.callsigns = ['TEST1*']
        watch_list.WatchList._instance = None
        wl = watch_list.WatchList()

        packet = fake.fake_packet(fromcall='TEST1')
        wl.rx(packet)

        # WatchList should track packets
        self.assertIn('TEST1', wl.data)
        self.assertIsNotNone(wl.data['TEST1']['last'])
        self.assertEqual(wl.data['TEST1']['packet'], packet)

    def test_rx_not_in_watchlist(self):
        """Test rx() with callsign not in watchlist."""
        wl = watch_list.WatchList()
        CONF.watch_list.callsigns = ['TEST1*']
        watch_list.WatchList._instance = None
        wl = watch_list.WatchList()

        packet = fake.fake_packet(fromcall='NOTINLIST')
        wl.rx(packet)

        # Should not add to data
        self.assertNotIn('NOTINLIST', wl.data)

    def test_rx_multiple(self):
        """Test rx() with multiple packets."""
        wl = watch_list.WatchList()
        CONF.watch_list.callsigns = ['TEST2*']
        watch_list.WatchList._instance = None
        wl = watch_list.WatchList()

        packet1 = fake.fake_packet(fromcall='TEST2')
        packet2 = fake.fake_packet(fromcall='TEST2', message='different')

        wl.rx(packet1)
        wl.rx(packet2)

        # Should track both, last packet should be packet2
        self.assertIn('TEST2', wl.data)
        self.assertEqual(wl.data['TEST2']['packet'], packet2)

    def test_tx(self):
        """Test tx() method (should be no-op)."""
        wl = watch_list.WatchList()
        packet = fake.fake_packet()

        # Should not raise exception
        wl.tx(packet)

    def test_last_seen(self):
        """Test last_seen() method."""
        wl = watch_list.WatchList()
        CONF.watch_list.callsigns = ['TEST3*']
        watch_list.WatchList._instance = None
        wl = watch_list.WatchList()

        packet = fake.fake_packet(fromcall='TEST3')
        wl.rx(packet)

        last_seen = wl.last_seen('TEST3')
        self.assertIsNotNone(last_seen)
        self.assertIsInstance(last_seen, datetime.datetime)

        self.assertIsNone(wl.last_seen('NOTINLIST'))

    def test_age(self):
        """Test age() method."""
        wl = watch_list.WatchList()
        CONF.watch_list.callsigns = ['TEST4*']
        watch_list.WatchList._instance = None
        wl = watch_list.WatchList()

        packet = fake.fake_packet(fromcall='TEST4')
        wl.rx(packet)

        age = wl.age('TEST4')
        self.assertIsNotNone(age)
        self.assertIsInstance(age, str)

        self.assertIsNone(wl.age('NOTINLIST'))

    def test_max_delta(self):
        """Test max_delta() method."""
        wl = watch_list.WatchList()

        delta = wl.max_delta(seconds=300)
        self.assertIsInstance(delta, datetime.timedelta)
        self.assertEqual(delta.total_seconds(), 300)

        # Test with config default
        delta = wl.max_delta()
        self.assertIsInstance(delta, datetime.timedelta)

    def test_is_old(self):
        """Test is_old() method."""
        wl = watch_list.WatchList()
        CONF.watch_list.callsigns = ['TEST5*']
        CONF.watch_list.alert_time_seconds = 60
        watch_list.WatchList._instance = None
        wl = watch_list.WatchList()

        # Not in watchlist
        self.assertFalse(wl.is_old('NOTINLIST'))

        # In watchlist but no last seen
        self.assertFalse(wl.is_old('TEST5'))

        # Add packet
        packet = fake.fake_packet(fromcall='TEST5')
        wl.rx(packet)

        # Should not be old immediately
        self.assertFalse(wl.is_old('TEST5'))

        # Test with custom seconds
        self.assertFalse(wl.is_old('TEST5', seconds=3600))
