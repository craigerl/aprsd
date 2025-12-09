import unittest
from unittest import mock

from aprsd.packets.filters.dupe_filter import DupePacketFilter
from tests import fake


class TestDupePacketFilter(unittest.TestCase):
    """Unit tests for the DupePacketFilter class."""

    def setUp(self):
        """Set up test fixtures."""
        self.filter = DupePacketFilter()
        from oslo_config import cfg

        CONF = cfg.CONF
        CONF.packet_dupe_timeout = 60

    def test_filter_ack_packet(self):
        """Test filter() with AckPacket (should always pass)."""
        packet = fake.fake_ack_packet()
        result = self.filter.filter(packet)
        self.assertEqual(result, packet)

    def test_filter_new_packet(self):
        """Test filter() with new packet."""
        packet = fake.fake_packet(msg_number='123')

        with mock.patch(
            'aprsd.packets.filters.dupe_filter.packets.PacketList'
        ) as mock_list:
            mock_list_instance = mock.MagicMock()
            mock_list_instance.find.side_effect = KeyError('Not found')
            mock_list.return_value = mock_list_instance

            result = self.filter.filter(packet)
            self.assertEqual(result, packet)

    def test_filter_packet_no_msgno(self):
        """Test filter() with packet without msgNo."""
        packet = fake.fake_packet()
        packet.msgNo = None

        with mock.patch(
            'aprsd.packets.filters.dupe_filter.packets.PacketList'
        ) as mock_list:
            mock_list_instance = mock.MagicMock()
            found_packet = fake.fake_packet()
            mock_list_instance.find.return_value = found_packet
            mock_list.return_value = mock_list_instance

            # Should pass even if found (no msgNo = can't detect dupe)
            result = self.filter.filter(packet)
            self.assertEqual(result, packet)

    def test_filter_unprocessed_duplicate(self):
        """Test filter() with duplicate but unprocessed packet."""
        packet = fake.fake_packet(msg_number='123')
        packet.processed = False

        with mock.patch(
            'aprsd.packets.filters.dupe_filter.packets.PacketList'
        ) as mock_list:
            mock_list_instance = mock.MagicMock()
            found_packet = fake.fake_packet(msg_number='123')
            mock_list_instance.find.return_value = found_packet
            mock_list.return_value = mock_list_instance

            result = self.filter.filter(packet)
            self.assertEqual(result, packet)

    def test_filter_duplicate_within_timeout(self):
        """Test filter() with duplicate within timeout."""
        from oslo_config import cfg

        CONF = cfg.CONF
        CONF.packet_dupe_timeout = 60

        packet = fake.fake_packet(msg_number='123')
        packet.processed = True
        packet.timestamp = 1000

        with mock.patch(
            'aprsd.packets.filters.dupe_filter.packets.PacketList'
        ) as mock_list:
            mock_list_instance = mock.MagicMock()
            found_packet = fake.fake_packet(msg_number='123')
            found_packet.timestamp = 1050  # Within 60 second timeout
            mock_list_instance.find.return_value = found_packet
            mock_list.return_value = mock_list_instance

            with mock.patch('aprsd.packets.filters.dupe_filter.LOG') as mock_log:
                result = self.filter.filter(packet)
                self.assertIsNone(result)  # Should be dropped
                mock_log.warning.assert_called()

    def test_filter_duplicate_after_timeout(self):
        """Test filter() with duplicate after timeout."""
        from oslo_config import cfg

        CONF = cfg.CONF
        CONF.packet_dupe_timeout = 60

        packet = fake.fake_packet(msg_number='123')
        packet.processed = True
        packet.timestamp = 2000

        with mock.patch(
            'aprsd.packets.filters.dupe_filter.packets.PacketList'
        ) as mock_list:
            mock_list_instance = mock.MagicMock()
            found_packet = fake.fake_packet(msg_number='123')
            found_packet.timestamp = 1000  # More than 60 seconds ago
            mock_list_instance.find.return_value = found_packet
            mock_list.return_value = mock_list_instance

            with mock.patch('aprsd.packets.filters.dupe_filter.LOG') as mock_log:
                result = self.filter.filter(packet)
                self.assertEqual(result, packet)  # Should pass
                mock_log.warning.assert_called()
