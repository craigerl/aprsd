import json
import unittest

import aprslib

from aprsd import packets
from tests import fake


class TestGPSPacket(unittest.TestCase):
    """Test GPSPacket JSON serialization."""

    def test_gps_packet_to_json(self):
        """Test GPSPacket.to_json() method."""
        packet = packets.GPSPacket(
            from_call=fake.FAKE_FROM_CALLSIGN,
            to_call=fake.FAKE_TO_CALLSIGN,
            latitude=37.7749,
            longitude=-122.4194,
            altitude=100.0,
            symbol='>',
            symbol_table='/',
            comment='Test GPS comment',
        )
        json_str = packet.to_json()
        self.assertIsInstance(json_str, str)
        json_dict = json.loads(json_str)
        self.assertEqual(json_dict['_type'], 'GPSPacket')
        self.assertEqual(json_dict['from_call'], fake.FAKE_FROM_CALLSIGN)
        self.assertEqual(json_dict['to_call'], fake.FAKE_TO_CALLSIGN)
        self.assertEqual(json_dict['latitude'], 37.7749)
        self.assertEqual(json_dict['longitude'], -122.4194)
        self.assertEqual(json_dict['altitude'], 100.0)
        self.assertEqual(json_dict['symbol'], '>')
        self.assertEqual(json_dict['symbol_table'], '/')
        self.assertEqual(json_dict['comment'], 'Test GPS comment')

    def test_gps_packet_from_dict(self):
        """Test GPSPacket.from_dict() method."""
        packet_dict = {
            '_type': 'GPSPacket',
            'from_call': fake.FAKE_FROM_CALLSIGN,
            'to_call': fake.FAKE_TO_CALLSIGN,
            'latitude': 37.7749,
            'longitude': -122.4194,
            'altitude': 100.0,
            'symbol': '>',
            'symbol_table': '/',
            'comment': 'Test GPS comment',
        }
        packet = packets.GPSPacket.from_dict(packet_dict)
        self.assertIsInstance(packet, packets.GPSPacket)
        self.assertEqual(packet.from_call, fake.FAKE_FROM_CALLSIGN)
        self.assertEqual(packet.to_call, fake.FAKE_TO_CALLSIGN)
        self.assertEqual(packet.latitude, 37.7749)
        self.assertEqual(packet.longitude, -122.4194)
        self.assertEqual(packet.altitude, 100.0)
        self.assertEqual(packet.symbol, '>')
        self.assertEqual(packet.symbol_table, '/')
        self.assertEqual(packet.comment, 'Test GPS comment')

    def test_gps_packet_round_trip(self):
        """Test GPSPacket round-trip: to_json -> from_dict."""
        original = packets.GPSPacket(
            from_call=fake.FAKE_FROM_CALLSIGN,
            to_call=fake.FAKE_TO_CALLSIGN,
            latitude=37.7749,
            longitude=-122.4194,
            altitude=100.0,
            symbol='>',
            symbol_table='/',
            comment='Test GPS comment',
            speed=25.5,
            course=180,
        )
        json_str = original.to_json()
        packet_dict = json.loads(json_str)
        restored = packets.GPSPacket.from_dict(packet_dict)
        self.assertEqual(restored.from_call, original.from_call)
        self.assertEqual(restored.to_call, original.to_call)
        self.assertEqual(restored.latitude, original.latitude)
        self.assertEqual(restored.longitude, original.longitude)
        self.assertEqual(restored.altitude, original.altitude)
        self.assertEqual(restored.symbol, original.symbol)
        self.assertEqual(restored.symbol_table, original.symbol_table)
        self.assertEqual(restored.comment, original.comment)
        self.assertEqual(restored.speed, original.speed)
        self.assertEqual(restored.course, original.course)
        self.assertEqual(restored._type, original._type)

    def test_gps_packet_from_raw_string(self):
        """Test GPSPacket creation from raw APRS string."""
        packet_raw = 'KFAKE>APZ100,WIDE2-1:!3742.00N/12225.00W>Test GPS comment'
        packet_dict = aprslib.parse(packet_raw)
        packet = packets.factory(packet_dict)
        # GPS packets are typically created as BeaconPacket or other types
        # but we can test if it has GPS data
        self.assertIsNotNone(packet)
        if hasattr(packet, 'latitude') and hasattr(packet, 'longitude'):
            # Test to_json
            json_str = packet.to_json()
            self.assertIsInstance(json_str, str)
            json_dict = json.loads(json_str)
            self.assertIn('latitude', json_dict)
            self.assertIn('longitude', json_dict)
            # Test from_dict round trip
            restored = packets.factory(json_dict)
            self.assertEqual(restored.latitude, packet.latitude)
            self.assertEqual(restored.longitude, packet.longitude)
