import json
import unittest

import aprslib

from aprsd import packets
from tests import fake


class TestThirdPartyPacket(unittest.TestCase):
    """Test ThirdPartyPacket JSON serialization."""

    def test_thirdparty_packet_to_json(self):
        """Test ThirdPartyPacket.to_json() method."""
        subpacket = packets.MessagePacket(
            from_call='SUB',
            to_call='TARGET',
            message_text='Sub message',
        )
        packet = packets.ThirdPartyPacket(
            from_call=fake.FAKE_FROM_CALLSIGN,
            to_call=fake.FAKE_TO_CALLSIGN,
            subpacket=subpacket,
        )
        json_str = packet.to_json()
        self.assertIsInstance(json_str, str)
        json_dict = json.loads(json_str)
        self.assertEqual(json_dict['_type'], 'ThirdPartyPacket')
        self.assertEqual(json_dict['from_call'], fake.FAKE_FROM_CALLSIGN)
        self.assertEqual(json_dict['to_call'], fake.FAKE_TO_CALLSIGN)
        # subpacket should be serialized as a dict
        self.assertIn('subpacket', json_dict)
        self.assertIsInstance(json_dict['subpacket'], dict)

    def test_thirdparty_packet_from_dict(self):
        """Test ThirdPartyPacket.from_dict() method."""
        subpacket_dict = {
            '_type': 'MessagePacket',
            'from_call': 'SUB',
            'to_call': 'TARGET',
            'message_text': 'Sub message',
        }
        packet_dict = {
            '_type': 'ThirdPartyPacket',
            'from_call': fake.FAKE_FROM_CALLSIGN,
            'to_call': fake.FAKE_TO_CALLSIGN,
            'subpacket': subpacket_dict,
        }
        packet = packets.ThirdPartyPacket.from_dict(packet_dict)
        self.assertIsInstance(packet, packets.ThirdPartyPacket)
        self.assertEqual(packet.from_call, fake.FAKE_FROM_CALLSIGN)
        self.assertEqual(packet.to_call, fake.FAKE_TO_CALLSIGN)
        self.assertIsNotNone(packet.subpacket)
        self.assertIsInstance(packet.subpacket, packets.MessagePacket)

    def test_thirdparty_packet_round_trip(self):
        """Test ThirdPartyPacket round-trip: to_json -> from_dict."""
        subpacket = packets.MessagePacket(
            from_call='SUB',
            to_call='TARGET',
            message_text='Sub message',
        )
        original = packets.ThirdPartyPacket(
            from_call=fake.FAKE_FROM_CALLSIGN,
            to_call=fake.FAKE_TO_CALLSIGN,
            subpacket=subpacket,
        )
        json_str = original.to_json()
        packet_dict = json.loads(json_str)
        restored = packets.ThirdPartyPacket.from_dict(packet_dict)
        self.assertEqual(restored.from_call, original.from_call)
        self.assertEqual(restored.to_call, original.to_call)
        self.assertEqual(restored._type, original._type)
        # Verify subpacket was restored
        self.assertIsNotNone(restored.subpacket)
        self.assertIsInstance(restored.subpacket, packets.MessagePacket)
        self.assertEqual(restored.subpacket.from_call, original.subpacket.from_call)
        self.assertEqual(restored.subpacket.to_call, original.subpacket.to_call)
        self.assertEqual(
            restored.subpacket.message_text, original.subpacket.message_text
        )

    def test_thirdparty_packet_from_raw_string(self):
        """Test ThirdPartyPacket creation from raw APRS string."""
        packet_raw = 'GTOWN>APDW16,WIDE1-1,WIDE2-1:}KM6LYW-9>APZ100,TCPIP,GTOWN*::KM6LYW   :KM6LYW: 19 Miles SW'
        packet_dict = aprslib.parse(packet_raw)
        packet = packets.factory(packet_dict)
        self.assertIsInstance(packet, packets.ThirdPartyPacket)
        # Test to_json
        json_str = packet.to_json()
        self.assertIsInstance(json_str, str)
        json_dict = json.loads(json_str)
        self.assertEqual(json_dict['_type'], 'ThirdPartyPacket')
        # Test from_dict round trip
        restored = packets.factory(json_dict)
        self.assertIsInstance(restored, packets.ThirdPartyPacket)
        self.assertEqual(restored.from_call, packet.from_call)
        self.assertIsNotNone(restored.subpacket)
        self.assertEqual(restored.subpacket.from_call, packet.subpacket.from_call)
