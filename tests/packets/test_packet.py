import json
import unittest

import aprslib

from aprsd import packets
from tests import fake


class TestPacket(unittest.TestCase):
    """Test Packet base class JSON serialization."""

    def test_packet_to_json(self):
        """Test Packet.to_json() method."""
        packet = packets.Packet(
            from_call=fake.FAKE_FROM_CALLSIGN,
            to_call=fake.FAKE_TO_CALLSIGN,
            msgNo='123',
        )
        json_str = packet.to_json()
        self.assertIsInstance(json_str, str)
        # Verify it's valid JSON
        json_dict = json.loads(json_str)
        self.assertEqual(json_dict['from_call'], fake.FAKE_FROM_CALLSIGN)
        self.assertEqual(json_dict['to_call'], fake.FAKE_TO_CALLSIGN)
        self.assertEqual(json_dict['msgNo'], '123')

    def test_packet_from_dict(self):
        """Test Packet.from_dict() method."""
        packet_dict = {
            '_type': 'Packet',
            'from_call': fake.FAKE_FROM_CALLSIGN,
            'to_call': fake.FAKE_TO_CALLSIGN,
            'msgNo': '123',
        }
        packet = packets.Packet.from_dict(packet_dict)
        self.assertIsInstance(packet, packets.Packet)
        self.assertEqual(packet.from_call, fake.FAKE_FROM_CALLSIGN)
        self.assertEqual(packet.to_call, fake.FAKE_TO_CALLSIGN)
        self.assertEqual(packet.msgNo, '123')

    def test_packet_round_trip(self):
        """Test Packet round-trip: to_json -> from_dict."""
        original = packets.Packet(
            from_call=fake.FAKE_FROM_CALLSIGN,
            to_call=fake.FAKE_TO_CALLSIGN,
            msgNo='123',
            addresse=fake.FAKE_TO_CALLSIGN,
        )
        json_str = original.to_json()
        packet_dict = json.loads(json_str)
        restored = packets.Packet.from_dict(packet_dict)
        self.assertEqual(restored.from_call, original.from_call)
        self.assertEqual(restored.to_call, original.to_call)
        self.assertEqual(restored.msgNo, original.msgNo)
        self.assertEqual(restored.addresse, original.addresse)

    def test_packet_from_raw_string(self):
        """Test Packet creation from raw APRS string."""
        # Note: Base Packet is rarely used directly, but we can test with a simple message
        packet_raw = 'KFAKE>APZ100::KMINE   :Test message{123'
        packet_dict = aprslib.parse(packet_raw)
        # aprslib might not set format correctly, so set it manually
        packet_dict['format'] = 'message'
        packet = packets.factory(packet_dict)
        self.assertIsInstance(packet, packets.MessagePacket)
        # Test to_json
        json_str = packet.to_json()
        self.assertIsInstance(json_str, str)
        json_dict = json.loads(json_str)
        self.assertIn('from_call', json_dict)
        # Test from_dict round trip
        restored = packets.factory(json_dict)
        self.assertEqual(restored.from_call, packet.from_call)
        self.assertEqual(restored.to_call, packet.to_call)
