import json
import unittest

import aprslib

from aprsd import packets
from tests import fake


class TestBulletinPacket(unittest.TestCase):
    """Test BulletinPacket JSON serialization."""

    def test_bulletin_packet_to_json(self):
        """Test BulletinPacket.to_json() method."""
        packet = packets.BulletinPacket(
            from_call=fake.FAKE_FROM_CALLSIGN,
            message_text='Test bulletin message',
            bid='1',
        )
        json_str = packet.to_json()
        self.assertIsInstance(json_str, str)
        json_dict = json.loads(json_str)
        self.assertEqual(json_dict['_type'], 'BulletinPacket')
        self.assertEqual(json_dict['from_call'], fake.FAKE_FROM_CALLSIGN)
        self.assertEqual(json_dict['message_text'], 'Test bulletin message')
        self.assertEqual(json_dict['bid'], '1')

    def test_bulletin_packet_from_dict(self):
        """Test BulletinPacket.from_dict() method."""
        packet_dict = {
            '_type': 'BulletinPacket',
            'from_call': fake.FAKE_FROM_CALLSIGN,
            'message_text': 'Test bulletin message',
            'bid': '1',
        }
        packet = packets.BulletinPacket.from_dict(packet_dict)
        self.assertIsInstance(packet, packets.BulletinPacket)
        self.assertEqual(packet.from_call, fake.FAKE_FROM_CALLSIGN)
        self.assertEqual(packet.message_text, 'Test bulletin message')
        self.assertEqual(packet.bid, '1')

    def test_bulletin_packet_round_trip(self):
        """Test BulletinPacket round-trip: to_json -> from_dict."""
        original = packets.BulletinPacket(
            from_call=fake.FAKE_FROM_CALLSIGN,
            message_text='Test bulletin message',
            bid='1',
        )
        json_str = original.to_json()
        packet_dict = json.loads(json_str)
        restored = packets.BulletinPacket.from_dict(packet_dict)
        self.assertEqual(restored.from_call, original.from_call)
        self.assertEqual(restored.message_text, original.message_text)
        self.assertEqual(restored.bid, original.bid)
        self.assertEqual(restored._type, original._type)

    def test_bulletin_packet_from_raw_string(self):
        """Test BulletinPacket creation from raw APRS string."""
        packet_raw = 'KFAKE>APZ100::BLN1     :Test bulletin message'
        packet_dict = aprslib.parse(packet_raw)
        # aprslib might not set format correctly, so set it manually
        packet_dict['format'] = 'bulletin'
        packet = packets.factory(packet_dict)
        self.assertIsInstance(packet, packets.BulletinPacket)
        # Test to_json
        json_str = packet.to_json()
        self.assertIsInstance(json_str, str)
        json_dict = json.loads(json_str)
        self.assertEqual(json_dict['_type'], 'BulletinPacket')
        # Test from_dict round trip
        restored = packets.factory(json_dict)
        self.assertIsInstance(restored, packets.BulletinPacket)
        self.assertEqual(restored.from_call, packet.from_call)
        self.assertEqual(restored.message_text, packet.message_text)
        self.assertEqual(restored.bid, packet.bid)
