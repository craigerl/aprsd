import datetime
import unittest
from unittest import mock

from aprsd.packets import seen_list
from tests import fake


class TestSeenList(unittest.TestCase):
    """Unit tests for the SeenList class."""

    def setUp(self):
        """Set up test fixtures."""
        # Reset singleton instance
        seen_list.SeenList._instance = None

    def tearDown(self):
        """Clean up after tests."""
        seen_list.SeenList._instance = None

    def test_singleton_pattern(self):
        """Test that SeenList is a singleton."""
        sl1 = seen_list.SeenList()
        sl2 = seen_list.SeenList()
        self.assertIs(sl1, sl2)

    def test_init(self):
        """Test initialization."""
        sl = seen_list.SeenList()
        self.assertEqual(sl.data, {})

    def test_stats(self):
        """Test stats() method."""
        sl = seen_list.SeenList()
        stats = sl.stats()
        self.assertIsInstance(stats, dict)

        stats_serializable = sl.stats(serializable=True)
        self.assertIsInstance(stats_serializable, dict)

    def test_rx(self):
        """Test rx() method."""
        sl = seen_list.SeenList()
        packet = fake.fake_packet(fromcall='TEST1')

        sl.rx(packet)

        self.assertIn('TEST1', sl.data)
        self.assertIn('last', sl.data['TEST1'])
        self.assertIn('count', sl.data['TEST1'])
        self.assertEqual(sl.data['TEST1']['count'], 1)
        self.assertIsInstance(sl.data['TEST1']['last'], datetime.datetime)

    def test_rx_multiple(self):
        """Test rx() with multiple packets from same callsign."""
        sl = seen_list.SeenList()
        packet1 = fake.fake_packet(fromcall='TEST2')
        packet2 = fake.fake_packet(fromcall='TEST2', message='different')

        sl.rx(packet1)
        sl.rx(packet2)

        self.assertEqual(sl.data['TEST2']['count'], 2)

    def test_rx_different_callsigns(self):
        """Test rx() with different callsigns."""
        sl = seen_list.SeenList()
        packet1 = fake.fake_packet(fromcall='TEST3')
        packet2 = fake.fake_packet(fromcall='TEST4')

        sl.rx(packet1)
        sl.rx(packet2)

        self.assertIn('TEST3', sl.data)
        self.assertIn('TEST4', sl.data)
        self.assertEqual(sl.data['TEST3']['count'], 1)
        self.assertEqual(sl.data['TEST4']['count'], 1)

    def test_rx_no_from_call(self):
        """Test rx() with packet missing from_call."""
        sl = seen_list.SeenList()

        class PacketWithoutFrom:
            from_call = None

        packet = PacketWithoutFrom()

        with mock.patch('aprsd.packets.seen_list.LOG') as mock_log:
            sl.rx(packet)
            mock_log.warning.assert_called()
            self.assertEqual(len(sl.data), 0)

    def test_tx(self):
        """Test tx() method (should be no-op)."""
        sl = seen_list.SeenList()
        packet = fake.fake_packet()

        # Should not raise exception
        sl.tx(packet)
        # Should not add to data
        self.assertEqual(len(sl.data), 0)

    def test_stats_with_data(self):
        """Test stats() with data."""
        sl = seen_list.SeenList()
        sl.rx(fake.fake_packet(fromcall='TEST5'))
        sl.rx(fake.fake_packet(fromcall='TEST6'))

        stats = sl.stats()
        self.assertIn('TEST5', stats)
        self.assertIn('TEST6', stats)
        self.assertIn('last', stats['TEST5'])
        self.assertIn('count', stats['TEST5'])
