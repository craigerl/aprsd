import json
import unittest

import aprslib

from aprsd import packets
from tests import fake


class TestStatusPacket(unittest.TestCase):
    """Test StatusPacket JSON serialization."""

    def test_status_packet_to_json(self):
        """Test StatusPacket.to_json() method."""
        packet = packets.StatusPacket(
            from_call=fake.FAKE_FROM_CALLSIGN,
            to_call=fake.FAKE_TO_CALLSIGN,
            status='Test status message',
            msgNo='123',
            messagecapable=True,
            comment='Test comment',
        )
        json_str = packet.to_json()
        self.assertIsInstance(json_str, str)
        json_dict = json.loads(json_str)
        self.assertEqual(json_dict['_type'], 'StatusPacket')
        self.assertEqual(json_dict['from_call'], fake.FAKE_FROM_CALLSIGN)
        self.assertEqual(json_dict['to_call'], fake.FAKE_TO_CALLSIGN)
        self.assertEqual(json_dict['status'], 'Test status message')
        self.assertEqual(json_dict['msgNo'], '123')
        self.assertEqual(json_dict['messagecapable'], True)
        self.assertEqual(json_dict['comment'], 'Test comment')

    def test_status_packet_from_dict(self):
        """Test StatusPacket.from_dict() method."""
        packet_dict = {
            '_type': 'StatusPacket',
            'from_call': fake.FAKE_FROM_CALLSIGN,
            'to_call': fake.FAKE_TO_CALLSIGN,
            'status': 'Test status message',
            'msgNo': '123',
            'messagecapable': True,
            'comment': 'Test comment',
        }
        packet = packets.StatusPacket.from_dict(packet_dict)
        self.assertIsInstance(packet, packets.StatusPacket)
        self.assertEqual(packet.from_call, fake.FAKE_FROM_CALLSIGN)
        self.assertEqual(packet.to_call, fake.FAKE_TO_CALLSIGN)
        self.assertEqual(packet.status, 'Test status message')
        self.assertEqual(packet.msgNo, '123')
        self.assertEqual(packet.messagecapable, True)
        self.assertEqual(packet.comment, 'Test comment')

    def test_status_packet_round_trip(self):
        """Test StatusPacket round-trip: to_json -> from_dict."""
        original = packets.StatusPacket(
            from_call=fake.FAKE_FROM_CALLSIGN,
            to_call=fake.FAKE_TO_CALLSIGN,
            status='Test status message',
            msgNo='123',
            messagecapable=True,
            comment='Test comment',
        )
        json_str = original.to_json()
        packet_dict = json.loads(json_str)
        restored = packets.StatusPacket.from_dict(packet_dict)
        self.assertEqual(restored.from_call, original.from_call)
        self.assertEqual(restored.to_call, original.to_call)
        self.assertEqual(restored.status, original.status)
        self.assertEqual(restored.msgNo, original.msgNo)
        self.assertEqual(restored.messagecapable, original.messagecapable)
        self.assertEqual(restored.comment, original.comment)
        self.assertEqual(restored._type, original._type)

    def test_status_packet_from_raw_string(self):
        """Test StatusPacket creation from raw APRS string."""
        packet_raw = 'KFAKE>APZ100::KMINE   :Test status message{123'
        packet_dict = aprslib.parse(packet_raw)
        # aprslib might not set format correctly, so set it manually
        packet_dict['format'] = 'status'
        packet = packets.factory(packet_dict)
        self.assertIsInstance(packet, packets.StatusPacket)
        # Test to_json
        json_str = packet.to_json()
        self.assertIsInstance(json_str, str)
        json_dict = json.loads(json_str)
        self.assertEqual(json_dict['_type'], 'StatusPacket')
        # Test from_dict round trip
        restored = packets.factory(json_dict)
        self.assertIsInstance(restored, packets.StatusPacket)
        self.assertEqual(restored.from_call, packet.from_call)
        self.assertEqual(restored.to_call, packet.to_call)
        self.assertEqual(restored.status, packet.status)
