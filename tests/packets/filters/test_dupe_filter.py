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

    def _deliver(self, packet, processed=True):
        """Mirror the RX thread: filter it, then mark it processed."""
        result = self.filter.filter(packet)
        if result is not None and processed:
            result.processed = True
        return result

    def test_filter_new_packet(self):
        """Test filter() with new packet."""
        packet = fake.fake_packet(msg_number='123')
        self.assertIs(self._deliver(packet), packet)

    def test_filter_packet_no_msgno(self):
        """Test filter() with packet without msgNo."""
        packet = fake.fake_packet()
        packet.msgNo = None

        # Should pass every time (no msgNo = can't detect dupe)
        self.assertIs(self._deliver(packet), packet)
        self.assertIs(self._deliver(packet), packet)

    def test_filter_unprocessed_duplicate(self):
        """Test filter() with duplicate but unprocessed packet."""
        packet = fake.fake_packet(msg_number='123')
        packet.timestamp = 1000
        self.assertIs(self._deliver(packet, processed=False), packet)

        retransmit = fake.fake_packet(msg_number='123')
        retransmit.timestamp = 1010
        self.assertIs(self._deliver(retransmit), retransmit)

    def test_filter_duplicate_within_timeout(self):
        """Test filter() with duplicate within timeout.

        The stored packet is already processed, so the new incoming
        duplicate should be dropped.
        """
        from oslo_config import cfg

        CONF = cfg.CONF
        CONF.packet_dupe_timeout = 60

        found_packet = fake.fake_packet(msg_number='123')
        found_packet.timestamp = 1000
        self._deliver(found_packet)

        packet = fake.fake_packet(msg_number='123')
        packet.timestamp = 1050  # Within 60 second timeout

        with mock.patch('aprsd.packets.filters.dupe_filter.LOG') as mock_log:
            self.assertIsNone(self._deliver(packet))  # Should be dropped
            mock_log.warning.assert_called()

    def test_filter_duplicate_after_timeout(self):
        """Test filter() with duplicate after timeout.

        The stored packet is already processed, but it arrived long ago
        (outside the dupe timeout window), so the new duplicate should be
        re-processed with a warning.
        """
        from oslo_config import cfg

        CONF = cfg.CONF
        CONF.packet_dupe_timeout = 60

        found_packet = fake.fake_packet(msg_number='123')
        found_packet.timestamp = 1000
        self._deliver(found_packet)

        packet = fake.fake_packet(msg_number='123')
        packet.timestamp = 2000  # More than 60 seconds ago

        with mock.patch('aprsd.packets.filters.dupe_filter.LOG') as mock_log:
            self.assertIs(self._deliver(packet), packet)  # Should pass
            mock_log.warning.assert_called()

    def test_dupe_survives_packet_list_eviction(self):
        """#320: a dupe inside packet_dupe_timeout must be dropped even after
        the packet has been evicted from PacketList's maxlen window.

        At ~0.33 pkt/s the 100-slot PacketList covers less than the 300s dupe
        timeout, so an old duplicate used to be treated as new and reprocessed.
        """
        from oslo_config import cfg

        CONF = cfg.CONF
        CONF.packet_dupe_timeout = 300

        first = fake.fake_packet(fromcall='DUPE1', msg_number='1')
        first.timestamp = 1000
        self.assertIs(self._deliver(first), first)

        # Enough distinct packets to evict DUPE1 from a 100-slot store.
        for i in range(150):
            other = fake.fake_packet(fromcall=f'OTHER{i}', msg_number=str(i))
            other.timestamp = 1001 + i
            self.assertIs(self._deliver(other), other)

        # Retransmit arrives 200s after the first copy, inside the 300s window.
        retransmit = fake.fake_packet(fromcall='DUPE1', msg_number='1')
        retransmit.timestamp = 1200
        self.assertIsNone(self._deliver(retransmit))

    def test_prune_drops_packets_outside_window(self):
        """_seen must not grow forever: entries older than the timeout go.

        Without _prune() the dupe answers stay correct (the time check is
        also done on lookup), so only this test notices the memory leak.
        """
        from oslo_config import cfg

        CONF = cfg.CONF
        CONF.packet_dupe_timeout = 60

        first = fake.fake_packet(msg_number='1')
        first.timestamp = 1000
        self._deliver(first)
        self.assertIn(first.key, self.filter._seen)

        later = fake.fake_packet(msg_number='2')
        later.timestamp = 1100  # 100s later, outside the 60s window
        self._deliver(later)

        self.assertNotIn(first.key, self.filter._seen)
        self.assertIn(later.key, self.filter._seen)

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

        # First receipt, already processed
        first_receipt = fake.fake_packet(msg_number='9028')
        first_receipt.timestamp = first_timestamp
        self._deliver(first_receipt)

        # Incoming duplicate — freshly decoded, processed=False (always)
        retransmit = fake.fake_packet(msg_number='9028')
        retransmit.timestamp = retransmit_timestamp

        with mock.patch('aprsd.packets.filters.dupe_filter.LOG') as mock_log:
            result = self.filter.filter(retransmit)
            self.assertIsNone(result)  # Must be dropped — no duplicate reply
            mock_log.warning.assert_called_once()
            warning_msg = mock_log.warning.call_args[0][0]
            self.assertIn('9028', warning_msg)
            self.assertIn('already tracked', warning_msg)
