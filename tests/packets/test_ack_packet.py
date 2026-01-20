import json
import unittest

import aprslib

from aprsd import packets
from tests import fake


class TestAckPacket(unittest.TestCase):
    """Test AckPacket JSON serialization."""

    def test_ack_packet_to_json(self):
        """Test AckPacket.to_json() method."""
        packet = packets.AckPacket(
            from_call=fake.FAKE_FROM_CALLSIGN,
            to_call=fake.FAKE_TO_CALLSIGN,
            msgNo='123',
        )
        json_str = packet.to_json()
        self.assertIsInstance(json_str, str)
        json_dict = json.loads(json_str)
        self.assertEqual(json_dict['_type'], 'AckPacket')
        self.assertEqual(json_dict['from_call'], fake.FAKE_FROM_CALLSIGN)
        self.assertEqual(json_dict['to_call'], fake.FAKE_TO_CALLSIGN)
        self.assertEqual(json_dict['msgNo'], '123')

    def test_ack_packet_from_dict(self):
        """Test AckPacket.from_dict() method."""
        packet_dict = {
            '_type': 'AckPacket',
            'from_call': fake.FAKE_FROM_CALLSIGN,
            'to_call': fake.FAKE_TO_CALLSIGN,
            'msgNo': '123',
        }
        packet = packets.AckPacket.from_dict(packet_dict)
        self.assertIsInstance(packet, packets.AckPacket)
        self.assertEqual(packet.from_call, fake.FAKE_FROM_CALLSIGN)
        self.assertEqual(packet.to_call, fake.FAKE_TO_CALLSIGN)
        self.assertEqual(packet.msgNo, '123')

    def test_ack_packet_round_trip(self):
        """Test AckPacket round-trip: to_json -> from_dict."""
        original = packets.AckPacket(
            from_call=fake.FAKE_FROM_CALLSIGN,
            to_call=fake.FAKE_TO_CALLSIGN,
            msgNo='123',
        )
        json_str = original.to_json()
        packet_dict = json.loads(json_str)
        restored = packets.AckPacket.from_dict(packet_dict)
        self.assertEqual(restored.from_call, original.from_call)
        self.assertEqual(restored.to_call, original.to_call)
        self.assertEqual(restored.msgNo, original.msgNo)
        self.assertEqual(restored._type, original._type)

    def test_ack_packet_from_raw_string(self):
        """Test AckPacket creation from raw APRS string."""
        packet_raw = 'KFAKE>APZ100::KMINE   :ack123'
        packet_dict = aprslib.parse(packet_raw)
        # aprslib might not set format/response correctly, so set them manually
        packet_dict['format'] = 'message'
        packet_dict['response'] = 'ack'
        packet = packets.factory(packet_dict)
        self.assertIsInstance(packet, packets.AckPacket)
        # Test to_json
        json_str = packet.to_json()
        self.assertIsInstance(json_str, str)
        json_dict = json.loads(json_str)
        self.assertEqual(json_dict['_type'], 'AckPacket')
        # Test from_dict round trip
        restored = packets.factory(json_dict)
        self.assertIsInstance(restored, packets.AckPacket)
        self.assertEqual(restored.from_call, packet.from_call)
        self.assertEqual(restored.to_call, packet.to_call)
        self.assertEqual(restored.msgNo, packet.msgNo)
