import json
import unittest

import aprslib

from aprsd import packets
from tests import fake


class TestMessagePacket(unittest.TestCase):
    """Test MessagePacket JSON serialization."""

    def test_message_packet_to_json(self):
        """Test MessagePacket.to_json() method."""
        packet = packets.MessagePacket(
            from_call=fake.FAKE_FROM_CALLSIGN,
            to_call=fake.FAKE_TO_CALLSIGN,
            message_text='Test message',
            msgNo='123',
        )
        json_str = packet.to_json()
        self.assertIsInstance(json_str, str)
        json_dict = json.loads(json_str)
        self.assertEqual(json_dict['_type'], 'MessagePacket')
        self.assertEqual(json_dict['from_call'], fake.FAKE_FROM_CALLSIGN)
        self.assertEqual(json_dict['to_call'], fake.FAKE_TO_CALLSIGN)
        self.assertEqual(json_dict['message_text'], 'Test message')
        self.assertEqual(json_dict['msgNo'], '123')

    def test_message_packet_from_dict(self):
        """Test MessagePacket.from_dict() method."""
        packet_dict = {
            '_type': 'MessagePacket',
            'from_call': fake.FAKE_FROM_CALLSIGN,
            'to_call': fake.FAKE_TO_CALLSIGN,
            'message_text': 'Test message',
            'msgNo': '123',
        }
        packet = packets.MessagePacket.from_dict(packet_dict)
        self.assertIsInstance(packet, packets.MessagePacket)
        self.assertEqual(packet.from_call, fake.FAKE_FROM_CALLSIGN)
        self.assertEqual(packet.to_call, fake.FAKE_TO_CALLSIGN)
        self.assertEqual(packet.message_text, 'Test message')
        self.assertEqual(packet.msgNo, '123')

    def test_message_packet_round_trip(self):
        """Test MessagePacket round-trip: to_json -> from_dict."""
        original = packets.MessagePacket(
            from_call=fake.FAKE_FROM_CALLSIGN,
            to_call=fake.FAKE_TO_CALLSIGN,
            message_text='Test message',
            msgNo='123',
        )
        json_str = original.to_json()
        packet_dict = json.loads(json_str)
        restored = packets.MessagePacket.from_dict(packet_dict)
        self.assertEqual(restored.from_call, original.from_call)
        self.assertEqual(restored.to_call, original.to_call)
        self.assertEqual(restored.message_text, original.message_text)
        self.assertEqual(restored.msgNo, original.msgNo)
        self.assertEqual(restored._type, original._type)

    def test_message_packet_from_raw_string(self):
        """Test MessagePacket creation from raw APRS string."""
        packet_raw = 'KM6LYW>APZ100::WB4BOR   :Test message{123'
        packet_dict = aprslib.parse(packet_raw)
        packet = packets.factory(packet_dict)
        self.assertIsInstance(packet, packets.MessagePacket)
        # Test to_json
        json_str = packet.to_json()
        self.assertIsInstance(json_str, str)
        json_dict = json.loads(json_str)
        self.assertEqual(json_dict['_type'], 'MessagePacket')
        # Test from_dict round trip
        restored = packets.factory(json_dict)
        self.assertIsInstance(restored, packets.MessagePacket)
        self.assertEqual(restored.from_call, packet.from_call)
        self.assertEqual(restored.to_call, packet.to_call)
        self.assertEqual(restored.message_text, packet.message_text)
        self.assertEqual(restored.msgNo, packet.msgNo)
