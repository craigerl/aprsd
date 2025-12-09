import unittest

from aprsd.packets import tracker
from tests import fake


class TestPacketTrack(unittest.TestCase):
    """Unit tests for the PacketTrack class."""

    def setUp(self):
        """Set up test fixtures."""
        # Reset singleton instance
        tracker.PacketTrack._instance = None
        tracker.PacketTrack.data = {}
        tracker.PacketTrack.total_tracked = 0

    def tearDown(self):
        """Clean up after tests."""
        tracker.PacketTrack._instance = None
        tracker.PacketTrack.data = {}
        tracker.PacketTrack.total_tracked = 0

    def test_singleton_pattern(self):
        """Test that PacketTrack is a singleton."""
        pt1 = tracker.PacketTrack()
        pt2 = tracker.PacketTrack()
        self.assertIs(pt1, pt2)

    def test_init(self):
        """Test initialization."""
        pt = tracker.PacketTrack()
        self.assertIsInstance(pt.data, dict)
        self.assertIsNotNone(pt._start_time)

    def test_getitem(self):
        """Test __getitem__() method."""
        pt = tracker.PacketTrack()
        packet = fake.fake_packet(msg_number='123')
        pt.tx(packet)

        result = pt['123']
        self.assertEqual(result, packet)

    def test_iter(self):
        """Test __iter__() method."""
        pt = tracker.PacketTrack()
        packet1 = fake.fake_packet(msg_number='123')
        packet2 = fake.fake_packet(msg_number='456')
        pt.tx(packet1)
        pt.tx(packet2)

        keys = list(iter(pt))
        self.assertIn('123', keys)
        self.assertIn('456', keys)

    def test_keys(self):
        """Test keys() method."""
        pt = tracker.PacketTrack()
        packet1 = fake.fake_packet(msg_number='123')
        packet2 = fake.fake_packet(msg_number='456')
        pt.tx(packet1)
        pt.tx(packet2)

        keys = list(pt.keys())
        self.assertIn('123', keys)
        self.assertIn('456', keys)

    def test_items(self):
        """Test items() method."""
        pt = tracker.PacketTrack()
        packet = fake.fake_packet(msg_number='123')
        pt.tx(packet)

        items = list(pt.items())
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0][0], '123')
        self.assertEqual(items[0][1], packet)

    def test_values(self):
        """Test values() method."""
        pt = tracker.PacketTrack()
        packet1 = fake.fake_packet(msg_number='123')
        packet2 = fake.fake_packet(msg_number='456')
        pt.tx(packet1)
        pt.tx(packet2)

        values = list(pt.values())
        self.assertEqual(len(values), 2)
        self.assertIn(packet1, values)
        self.assertIn(packet2, values)

    def test_tx(self):
        """Test tx() method."""
        pt = tracker.PacketTrack()
        packet = fake.fake_packet(msg_number='123')
        initial_total = pt.total_tracked

        pt.tx(packet)

        self.assertIn('123', pt.data)
        self.assertEqual(pt.data['123'], packet)
        self.assertEqual(pt.total_tracked, initial_total + 1)
        self.assertEqual(packet.send_count, 0)

    def test_rx_ack_packet(self):
        """Test rx() with AckPacket."""
        pt = tracker.PacketTrack()
        packet = fake.fake_packet(msg_number='123')
        pt.tx(packet)

        ack = fake.fake_ack_packet()
        ack.msgNo = '123'
        pt.rx(ack)

        self.assertNotIn('123', pt.data)

    def test_rx_reject_packet(self):
        """Test rx() with RejectPacket."""
        from aprsd.packets import core

        pt = tracker.PacketTrack()
        packet = fake.fake_packet(msg_number='123')
        pt.tx(packet)

        # Create a proper RejectPacket
        reject_pkt = core.RejectPacket(from_call='TEST', to_call='TEST', msgNo='123')
        pt.rx(reject_pkt)

        self.assertNotIn('123', pt.data)

    def test_rx_piggyback_ack(self):
        """Test rx() with piggyback ACK."""
        pt = tracker.PacketTrack()
        packet = fake.fake_packet(msg_number='123')
        pt.tx(packet)

        piggyback = fake.fake_packet()
        piggyback.ackMsgNo = '123'
        pt.rx(piggyback)

        self.assertNotIn('123', pt.data)

    def test_rx_no_match(self):
        """Test rx() with packet that doesn't match tracked packet."""
        pt = tracker.PacketTrack()
        packet = fake.fake_packet(msg_number='123')
        pt.tx(packet)

        ack = fake.fake_ack_packet()
        ack.msgNo = '999'  # Different msgNo
        pt.rx(ack)

        # Should still have original packet
        self.assertIn('123', pt.data)

    def test_remove(self):
        """Test remove() method."""
        pt = tracker.PacketTrack()
        packet = fake.fake_packet(msg_number='123')
        pt.tx(packet)

        pt.remove('123')
        self.assertNotIn('123', pt.data)

    def test_remove_nonexistent(self):
        """Test remove() with nonexistent key."""
        pt = tracker.PacketTrack()
        # Should not raise exception
        pt.remove('nonexistent')

    def test_stats(self):
        """Test stats() method."""
        pt = tracker.PacketTrack()
        packet = fake.fake_packet(msg_number='123')
        packet.retry_count = 3
        packet.last_send_time = 1000
        pt.tx(packet)
        # Note: tx() resets send_count to 0

        stats = pt.stats()
        self.assertIn('total_tracked', stats)
        self.assertIn('packets', stats)
        self.assertIn('123', stats['packets'])
        self.assertEqual(stats['packets']['123']['send_count'], 0)
        self.assertEqual(stats['packets']['123']['retry_count'], 3)

    def test_stats_serializable(self):
        """Test stats() with serializable=True."""
        pt = tracker.PacketTrack()
        packet = fake.fake_packet(msg_number='123')
        pt.tx(packet)

        stats = pt.stats(serializable=True)
        # Should be JSON serializable
        import json

        json.dumps(stats)  # Should not raise exception

    def test_get(self):
        """Test get() method from ObjectStoreMixin."""
        pt = tracker.PacketTrack()
        packet = fake.fake_packet(msg_number='123')
        pt.tx(packet)

        result = pt.get('123')
        self.assertEqual(result, packet)

        result = pt.get('nonexistent')
        self.assertIsNone(result)

    def test_len(self):
        """Test __len__() method."""
        pt = tracker.PacketTrack()
        self.assertEqual(len(pt), 0)

        pt.tx(fake.fake_packet(msg_number='123'))
        self.assertEqual(len(pt), 1)

        pt.tx(fake.fake_packet(msg_number='456'))
        self.assertEqual(len(pt), 2)
