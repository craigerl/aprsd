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
        """Test filter() with duplicate within timeout.

        The found (previously stored) packet is already processed.
        The new incoming duplicate should be dropped.
        """
        from oslo_config import cfg

        CONF = cfg.CONF
        CONF.packet_dupe_timeout = 60

        packet = fake.fake_packet(msg_number='123')
        packet.timestamp = 1000

        mock_list_instance = mock.MagicMock()
        found_packet = fake.fake_packet(msg_number='123')
        found_packet.processed = True  # the stored packet was already processed
        found_packet.timestamp = 1050  # Within 60 second timeout
        mock_list_instance.find.return_value = found_packet
        self.filter.pl = mock_list_instance

        with mock.patch('aprsd.packets.filters.dupe_filter.LOG') as mock_log:
            result = self.filter.filter(packet)
            self.assertIsNone(result)  # Should be dropped
            mock_log.warning.assert_called()

    def test_filter_duplicate_after_timeout(self):
        """Test filter() with duplicate after timeout.

        The found (previously stored) packet is already processed,
        but it arrived long ago (outside the dupe timeout window).
        The new incoming duplicate should be re-processed with a warning.
        """
        from oslo_config import cfg

        CONF = cfg.CONF
        CONF.packet_dupe_timeout = 60

        packet = fake.fake_packet(msg_number='123')
        packet.timestamp = 2000

        mock_list_instance = mock.MagicMock()
        found_packet = fake.fake_packet(msg_number='123')
        found_packet.processed = True  # the stored packet was already processed
        found_packet.timestamp = 1000  # More than 60 seconds ago
        mock_list_instance.find.return_value = found_packet
        self.filter.pl = mock_list_instance

        with mock.patch('aprsd.packets.filters.dupe_filter.LOG') as mock_log:
            result = self.filter.filter(packet)
            self.assertEqual(result, packet)  # Should pass
            mock_log.warning.assert_called()

    def test_filter_aprs_retransmit_via_different_digi(self):
        """Regression test for the production duplicate-reply bug.

        Scenario (observed 2026-06-02 in aprsd-REPEAT logs):
          09:49:14  RX MessagePacket:9028  KM6LYW→...→qAO→KM6LYW-2→REPEAT  "N 2"
                    → processed, NearestPlugin replies sent (msg 2385, 2386)
          09:49:47  TX AckPacket:9028 (2 of 3)  ← KM6LYW never got the ack
          09:50:17  RX MessagePacket:9028  KM6LYW→...→qAR→GTOWN→REPEAT  "N 2"
                    ← same msgNo, different digipeater path, 63 seconds later
                    → BUG: DupePacketFilter passed it through because it was
                       checking packet.processed (new packet, always False)
                       instead of found.processed (stored packet, True)
                    → NearestPlugin ran again → 4 replies sent instead of 2

        The fix: check found.processed, not packet.processed.
        """
        from oslo_config import cfg

        CONF = cfg.CONF
        CONF.packet_dupe_timeout = 300  # 5 minute default

        # The retransmit arrives 63 seconds after the first receipt.
        first_timestamp = 1000.0
        retransmit_timestamp = first_timestamp + 63

        # Incoming duplicate — freshly decoded, processed=False (always)
        retransmit = fake.fake_packet(msg_number='9028')
        retransmit.timestamp = retransmit_timestamp

        # What PacketList holds from the first receipt — already processed
        first_receipt = fake.fake_packet(msg_number='9028')
        first_receipt.processed = True
        first_receipt.timestamp = first_timestamp

        mock_list_instance = mock.MagicMock()
        mock_list_instance.find.return_value = first_receipt
        self.filter.pl = mock_list_instance

        with mock.patch('aprsd.packets.filters.dupe_filter.LOG') as mock_log:
            result = self.filter.filter(retransmit)
            self.assertIsNone(result)  # Must be dropped — no duplicate reply
            mock_log.warning.assert_called_once()
            warning_msg = mock_log.warning.call_args[0][0]
            self.assertIn('9028', warning_msg)
            self.assertIn('already tracked', warning_msg)
