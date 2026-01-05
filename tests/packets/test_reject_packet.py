import json
import unittest

import aprslib

from aprsd import packets
from tests import fake


class TestRejectPacket(unittest.TestCase):
    """Test RejectPacket JSON serialization."""

    def test_reject_packet_to_json(self):
        """Test RejectPacket.to_json() method."""
        packet = packets.RejectPacket(
            from_call=fake.FAKE_FROM_CALLSIGN,
            to_call=fake.FAKE_TO_CALLSIGN,
            msgNo='123',
            response='rej',
        )
        json_str = packet.to_json()
        self.assertIsInstance(json_str, str)
        json_dict = json.loads(json_str)
        self.assertEqual(json_dict['_type'], 'RejectPacket')
        self.assertEqual(json_dict['from_call'], fake.FAKE_FROM_CALLSIGN)
        self.assertEqual(json_dict['to_call'], fake.FAKE_TO_CALLSIGN)
        self.assertEqual(json_dict['msgNo'], '123')

    def test_reject_packet_from_dict(self):
        """Test RejectPacket.from_dict() method."""
        packet_dict = {
            '_type': 'RejectPacket',
            'from_call': fake.FAKE_FROM_CALLSIGN,
            'to_call': fake.FAKE_TO_CALLSIGN,
            'msgNo': '123',
            'response': 'rej',
        }
        packet = packets.RejectPacket.from_dict(packet_dict)
        self.assertIsInstance(packet, packets.RejectPacket)
        self.assertEqual(packet.from_call, fake.FAKE_FROM_CALLSIGN)
        self.assertEqual(packet.to_call, fake.FAKE_TO_CALLSIGN)
        self.assertEqual(packet.msgNo, '123')

    def test_reject_packet_round_trip(self):
        """Test RejectPacket round-trip: to_json -> from_dict."""
        original = packets.RejectPacket(
            from_call=fake.FAKE_FROM_CALLSIGN,
            to_call=fake.FAKE_TO_CALLSIGN,
            msgNo='123',
            response='rej',
        )
        json_str = original.to_json()
        packet_dict = json.loads(json_str)
        restored = packets.RejectPacket.from_dict(packet_dict)
        self.assertEqual(restored.from_call, original.from_call)
        self.assertEqual(restored.to_call, original.to_call)
        self.assertEqual(restored.msgNo, original.msgNo)
        self.assertEqual(restored._type, original._type)

    def test_reject_packet_from_raw_string(self):
        """Test RejectPacket creation from raw APRS string."""
        packet_raw = 'HB9FDL-1>APK102,HB9FM-4*,WIDE2,qAR,HB9FEF-11::REPEAT   :rej4139'
        packet_dict = aprslib.parse(packet_raw)
        packet = packets.factory(packet_dict)
        self.assertIsInstance(packet, packets.RejectPacket)
        # Test to_json
        json_str = packet.to_json()
        self.assertIsInstance(json_str, str)
        json_dict = json.loads(json_str)
        self.assertEqual(json_dict['_type'], 'RejectPacket')
        # Test from_dict round trip
        restored = packets.factory(json_dict)
        self.assertIsInstance(restored, packets.RejectPacket)
        self.assertEqual(restored.from_call, packet.from_call)
        self.assertEqual(restored.to_call, packet.to_call)
        self.assertEqual(restored.msgNo, packet.msgNo)
