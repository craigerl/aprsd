import json
import unittest

import aprslib

from aprsd import packets
from tests import fake


class TestObjectPacket(unittest.TestCase):
    """Test ObjectPacket JSON serialization."""

    def test_object_packet_to_json(self):
        """Test ObjectPacket.to_json() method."""
        packet = packets.ObjectPacket(
            from_call=fake.FAKE_FROM_CALLSIGN,
            to_call=fake.FAKE_TO_CALLSIGN,
            latitude=37.7749,
            longitude=-122.4194,
            symbol='r',
            symbol_table='/',
            comment='Test object comment',
            alive=True,
            speed=25.5,
            course=180,
        )
        json_str = packet.to_json()
        self.assertIsInstance(json_str, str)
        json_dict = json.loads(json_str)
        self.assertEqual(json_dict['_type'], 'ObjectPacket')
        self.assertEqual(json_dict['from_call'], fake.FAKE_FROM_CALLSIGN)
        self.assertEqual(json_dict['to_call'], fake.FAKE_TO_CALLSIGN)
        self.assertEqual(json_dict['latitude'], 37.7749)
        self.assertEqual(json_dict['longitude'], -122.4194)
        self.assertEqual(json_dict['symbol'], 'r')
        self.assertEqual(json_dict['symbol_table'], '/')
        self.assertEqual(json_dict['comment'], 'Test object comment')
        self.assertEqual(json_dict['alive'], True)
        self.assertEqual(json_dict['speed'], 25.5)
        self.assertEqual(json_dict['course'], 180)

    def test_object_packet_from_dict(self):
        """Test ObjectPacket.from_dict() method."""
        packet_dict = {
            '_type': 'ObjectPacket',
            'from_call': fake.FAKE_FROM_CALLSIGN,
            'to_call': fake.FAKE_TO_CALLSIGN,
            'latitude': 37.7749,
            'longitude': -122.4194,
            'symbol': 'r',
            'symbol_table': '/',
            'comment': 'Test object comment',
            'alive': True,
            'speed': 25.5,
            'course': 180,
        }
        packet = packets.ObjectPacket.from_dict(packet_dict)
        self.assertIsInstance(packet, packets.ObjectPacket)
        self.assertEqual(packet.from_call, fake.FAKE_FROM_CALLSIGN)
        self.assertEqual(packet.to_call, fake.FAKE_TO_CALLSIGN)
        self.assertEqual(packet.latitude, 37.7749)
        self.assertEqual(packet.longitude, -122.4194)
        self.assertEqual(packet.symbol, 'r')
        self.assertEqual(packet.symbol_table, '/')
        self.assertEqual(packet.comment, 'Test object comment')
        self.assertEqual(packet.alive, True)
        self.assertEqual(packet.speed, 25.5)
        self.assertEqual(packet.course, 180)

    def test_object_packet_round_trip(self):
        """Test ObjectPacket round-trip: to_json -> from_dict."""
        original = packets.ObjectPacket(
            from_call=fake.FAKE_FROM_CALLSIGN,
            to_call=fake.FAKE_TO_CALLSIGN,
            latitude=37.7749,
            longitude=-122.4194,
            symbol='r',
            symbol_table='/',
            comment='Test object comment',
            alive=True,
            speed=25.5,
            course=180,
        )
        json_str = original.to_json()
        packet_dict = json.loads(json_str)
        restored = packets.ObjectPacket.from_dict(packet_dict)
        self.assertEqual(restored.from_call, original.from_call)
        self.assertEqual(restored.to_call, original.to_call)
        self.assertEqual(restored.latitude, original.latitude)
        self.assertEqual(restored.longitude, original.longitude)
        self.assertEqual(restored.symbol, original.symbol)
        self.assertEqual(restored.symbol_table, original.symbol_table)
        self.assertEqual(restored.comment, original.comment)
        self.assertEqual(restored.alive, original.alive)
        self.assertEqual(restored.speed, original.speed)
        self.assertEqual(restored.course, original.course)
        self.assertEqual(restored._type, original._type)

    def test_object_packet_from_raw_string(self):
        """Test ObjectPacket creation from raw APRS string."""
        # Use a working object packet example from the codebase
        packet_raw = (
            'REPEAT>APZ100:;K4CQ     *301301z3735.11N/07903.08Wr145.490MHz T136 -060'
        )
        packet_dict = aprslib.parse(packet_raw)
        # aprslib might not set format correctly, so set it manually
        packet_dict['format'] = 'object'
        packet = packets.factory(packet_dict)
        self.assertIsInstance(packet, packets.ObjectPacket)
        # Test to_json
        json_str = packet.to_json()
        self.assertIsInstance(json_str, str)
        json_dict = json.loads(json_str)
        self.assertEqual(json_dict['_type'], 'ObjectPacket')
        # Test from_dict round trip
        restored = packets.factory(json_dict)
        self.assertIsInstance(restored, packets.ObjectPacket)
        self.assertEqual(restored.from_call, packet.from_call)
        self.assertEqual(restored.to_call, packet.to_call)
        if hasattr(packet, 'latitude') and packet.latitude:
            self.assertEqual(restored.latitude, packet.latitude)
            self.assertEqual(restored.longitude, packet.longitude)
