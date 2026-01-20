import json
import unittest

import aprslib

from aprsd import packets
from tests import fake


class TestUnknownPacket(unittest.TestCase):
    """Test UnknownPacket JSON serialization."""

    def test_unknown_packet_to_json(self):
        """Test UnknownPacket.to_json() method."""
        packet = packets.UnknownPacket(
            from_call=fake.FAKE_FROM_CALLSIGN,
            to_call=fake.FAKE_TO_CALLSIGN,
            format='unknown_format',
            packet_type='unknown',
            unknown_fields={'extra_field': 'extra_value'},
        )
        json_str = packet.to_json()
        self.assertIsInstance(json_str, str)
        json_dict = json.loads(json_str)
        self.assertEqual(json_dict['_type'], 'UnknownPacket')
        self.assertEqual(json_dict['from_call'], fake.FAKE_FROM_CALLSIGN)
        self.assertEqual(json_dict['to_call'], fake.FAKE_TO_CALLSIGN)
        self.assertEqual(json_dict['format'], 'unknown_format')
        self.assertEqual(json_dict['packet_type'], 'unknown')

    def test_unknown_packet_from_dict(self):
        """Test UnknownPacket.from_dict() method."""
        packet_dict = {
            '_type': 'UnknownPacket',
            'from_call': fake.FAKE_FROM_CALLSIGN,
            'to_call': fake.FAKE_TO_CALLSIGN,
            'format': 'unknown_format',
            'packet_type': 'unknown',
            'extra_field': 'extra_value',
        }
        packet = packets.UnknownPacket.from_dict(packet_dict)
        self.assertIsInstance(packet, packets.UnknownPacket)
        self.assertEqual(packet.from_call, fake.FAKE_FROM_CALLSIGN)
        self.assertEqual(packet.to_call, fake.FAKE_TO_CALLSIGN)
        self.assertEqual(packet.format, 'unknown_format')
        self.assertEqual(packet.packet_type, 'unknown')

    def test_unknown_packet_round_trip(self):
        """Test UnknownPacket round-trip: to_json -> from_dict."""
        original = packets.UnknownPacket(
            from_call=fake.FAKE_FROM_CALLSIGN,
            to_call=fake.FAKE_TO_CALLSIGN,
            format='unknown_format',
            packet_type='unknown',
            unknown_fields={'extra_field': 'extra_value'},
        )
        json_str = original.to_json()
        packet_dict = json.loads(json_str)
        restored = packets.UnknownPacket.from_dict(packet_dict)
        self.assertEqual(restored.from_call, original.from_call)
        self.assertEqual(restored.to_call, original.to_call)
        self.assertEqual(restored.format, original.format)
        self.assertEqual(restored.packet_type, original.packet_type)
        self.assertEqual(restored._type, original._type)

    def test_unknown_packet_from_raw_string(self):
        """Test UnknownPacket creation from raw APRS string."""
        # Use a packet format that might not be recognized
        packet_raw = 'KFAKE>APZ100:>Unknown format data'
        packet_dict = aprslib.parse(packet_raw)
        packet = packets.factory(packet_dict)
        # This might be UnknownPacket or another type depending on parsing
        self.assertIsNotNone(packet)
        # Test to_json
        json_str = packet.to_json()
        self.assertIsInstance(json_str, str)
        json_dict = json.loads(json_str)
        # Test from_dict round trip
        restored = packets.factory(json_dict)
        self.assertEqual(restored.from_call, packet.from_call)
        if isinstance(packet, packets.UnknownPacket):
            self.assertIsInstance(restored, packets.UnknownPacket)
