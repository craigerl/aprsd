import unittest

from aprsd.packets.filters.packet_type import PacketTypeFilter
from tests import fake


class TestPacketTypeFilter(unittest.TestCase):
    """Unit tests for the PacketTypeFilter class."""

    def setUp(self):
        """Set up test fixtures."""
        # Reset singleton instance
        PacketTypeFilter._instance = None
        self.filter = PacketTypeFilter()

    def tearDown(self):
        """Clean up after tests."""
        PacketTypeFilter._instance = None

    def test_singleton_pattern(self):
        """Test that PacketTypeFilter is a singleton."""
        filter1 = PacketTypeFilter()
        filter2 = PacketTypeFilter()
        self.assertIs(filter1, filter2)

    def test_init(self):
        """Test initialization."""
        # Default allow_list includes Packet base class
        from aprsd import packets

        self.assertIn(packets.Packet, self.filter.allow_list)

    def test_set_allow_list(self):
        """Test set_allow_list() method."""
        from aprsd import packets as aprsd_packets

        filter_list = ['MessagePacket', 'AckPacket']
        self.filter.set_allow_list(filter_list)

        self.assertEqual(len(self.filter.allow_list), 2)
        self.assertIn(aprsd_packets.MessagePacket, self.filter.allow_list)
        self.assertIn(aprsd_packets.AckPacket, self.filter.allow_list)

    def test_filter_no_allow_list(self):
        """Test filter() with no allow list (all packets pass)."""
        packet = fake.fake_packet()
        result = self.filter.filter(packet)
        self.assertEqual(result, packet)

    def test_filter_allowed_type(self):
        """Test filter() with allowed packet type."""
        self.filter.set_allow_list(['MessagePacket'])
        packet = fake.fake_packet()

        result = self.filter.filter(packet)
        self.assertEqual(result, packet)

    def test_filter_not_allowed_type(self):
        """Test filter() with not allowed packet type."""
        self.filter.set_allow_list(['AckPacket'])
        packet = fake.fake_packet()  # MessagePacket

        result = self.filter.filter(packet)
        self.assertIsNone(result)

    def test_filter_multiple_types(self):
        """Test filter() with multiple allowed types."""
        self.filter.set_allow_list(['MessagePacket', 'AckPacket', 'BeaconPacket'])

        message_packet = fake.fake_packet()
        ack_packet = fake.fake_ack_packet()

        result1 = self.filter.filter(message_packet)
        result2 = self.filter.filter(ack_packet)

        self.assertEqual(result1, message_packet)
        self.assertEqual(result2, ack_packet)

    def test_filter_subclass(self):
        """Test filter() with subclass of allowed type."""
        # Set allow list to base Packet class
        self.filter.set_allow_list(['Packet'])

        # All packet types should pass
        message_packet = fake.fake_packet()
        result = self.filter.filter(message_packet)
        self.assertEqual(result, message_packet)
