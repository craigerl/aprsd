import unittest
from collections import OrderedDict

from oslo_config import cfg

from aprsd.packets import packet_list
from tests import fake

CONF = cfg.CONF


class TestPacketList(unittest.TestCase):
    """Unit tests for the PacketList class."""

    def setUp(self):
        """Set up test fixtures."""
        # Reset singleton instance and class variables
        packet_list.PacketList._instance = None
        packet_list.PacketList._total_rx = 0
        packet_list.PacketList._total_tx = 0
        # Mock config
        CONF.packet_list_maxlen = 100
        # Create fresh instance and reset data
        pl = packet_list.PacketList()
        pl.data = {'types': {}, 'packets': OrderedDict()}
        pl._total_rx = 0
        pl._total_tx = 0

    def tearDown(self):
        """Clean up after tests."""
        packet_list.PacketList._instance = None
        packet_list.PacketList._total_rx = 0
        packet_list.PacketList._total_tx = 0

    def test_singleton_pattern(self):
        """Test that PacketList is a singleton."""
        pl1 = packet_list.PacketList()
        pl2 = packet_list.PacketList()
        self.assertIs(pl1, pl2)

    def test_init(self):
        """Test initialization."""
        pl = packet_list.PacketList()
        self.assertEqual(pl.maxlen, 100)
        self.assertIn('types', pl.data)
        self.assertIn('packets', pl.data)

    def test_rx(self):
        """Test rx() method."""
        pl = packet_list.PacketList()
        packet = fake.fake_packet()

        initial_rx = pl._total_rx
        pl.rx(packet)

        self.assertEqual(pl._total_rx, initial_rx + 1)
        self.assertIn(packet.key, pl.data['packets'])
        self.assertIn(packet.__class__.__name__, pl.data['types'])

    def test_tx(self):
        """Test tx() method."""
        pl = packet_list.PacketList()
        packet = fake.fake_packet()

        initial_tx = pl._total_tx
        pl.tx(packet)

        self.assertEqual(pl._total_tx, initial_tx + 1)
        self.assertIn(packet.key, pl.data['packets'])
        self.assertIn(packet.__class__.__name__, pl.data['types'])

    def test_add(self):
        """Test add() method."""
        pl = packet_list.PacketList()
        packet = fake.fake_packet()

        pl.add(packet)
        self.assertIn(packet.key, pl.data['packets'])

    def test_find(self):
        """Test find() method."""
        pl = packet_list.PacketList()
        packet = fake.fake_packet()
        pl.add(packet)

        found = pl.find(packet)
        self.assertEqual(found, packet)

    def test_len(self):
        """Test __len__() method."""
        pl = packet_list.PacketList()
        self.assertEqual(len(pl), 0)

        packet1 = fake.fake_packet(fromcall='TEST1')
        pl.add(packet1)
        self.assertEqual(len(pl), 1)

        packet2 = fake.fake_packet(fromcall='TEST2', message='different')
        pl.add(packet2)
        self.assertEqual(len(pl), 2)

    def test_total_rx(self):
        """Test total_rx() method."""
        pl = packet_list.PacketList()
        pl.rx(fake.fake_packet())
        pl.rx(fake.fake_packet(message='test2'))

        self.assertEqual(pl.total_rx(), 2)

    def test_total_tx(self):
        """Test total_tx() method."""
        pl = packet_list.PacketList()
        pl.tx(fake.fake_packet())
        pl.tx(fake.fake_packet(message='test2'))

        self.assertEqual(pl.total_tx(), 2)

    def test_maxlen_enforcement(self):
        """Test that maxlen is enforced."""
        CONF.packet_list_maxlen = 3
        packet_list.PacketList._instance = None
        packet_list.PacketList._total_rx = 0
        packet_list.PacketList._total_tx = 0
        pl = packet_list.PacketList()
        pl.data = {'types': {}, 'packets': OrderedDict()}
        pl._total_rx = 0
        pl._total_tx = 0

        # Add more than maxlen with different keys
        for i in range(5):
            packet = fake.fake_packet(fromcall=f'TEST{i}', message=f'test{i}')
            pl.add(packet)

        # Should only have maxlen packets
        self.assertEqual(len(pl), 3)
        # Oldest should be removed
        self.assertNotIn(fake.fake_packet(message='test0').key, pl.data['packets'])

    def test_duplicate_packet(self):
        """Test that duplicate packets move to end."""
        pl = packet_list.PacketList()
        packet = fake.fake_packet(message='test')

        pl.add(packet)
        # Add different packet
        pl.add(fake.fake_packet(message='other'))
        # Add original packet again
        pl.add(packet)

        # Original packet should be at end
        keys = list(pl.data['packets'].keys())
        self.assertEqual(keys[-1], packet.key)

    def test_stats(self):
        """Test stats() method."""
        pl = packet_list.PacketList()
        pl.rx(fake.fake_packet())
        pl.tx(fake.fake_packet(message='test2'))

        stats = pl.stats()
        self.assertIn('rx', stats)
        self.assertIn('tx', stats)
        self.assertIn('total_tracked', stats)
        self.assertIn('types', stats)
        self.assertEqual(stats['rx'], 1)
        self.assertEqual(stats['tx'], 1)

    def test_stats_serializable(self):
        """Test stats() with serializable=True."""
        pl = packet_list.PacketList()
        pl.rx(fake.fake_packet())

        stats = pl.stats(serializable=True)
        # Note: packets in stats are not JSON serializable by default
        # This test just verifies the method accepts the parameter
        self.assertIsInstance(stats, dict)
        self.assertIn('rx', stats)

    def test_type_stats(self):
        """Test that type statistics are tracked."""
        pl = packet_list.PacketList()
        packet1 = fake.fake_packet()
        packet2 = fake.fake_packet(message='test2')

        pl.rx(packet1)
        pl.rx(packet2)
        pl.tx(packet1)

        stats = pl.stats()
        packet_type = packet1.__class__.__name__
        self.assertIn(packet_type, stats['types'])
        self.assertEqual(stats['types'][packet_type]['rx'], 2)
        self.assertEqual(stats['types'][packet_type]['tx'], 1)
