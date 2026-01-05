import json
import unittest

import aprslib

from aprsd import packets
from tests import fake


class TestBeaconPacket(unittest.TestCase):
    """Test BeaconPacket JSON serialization."""

    def test_beacon_packet_to_json(self):
        """Test BeaconPacket.to_json() method."""
        packet = packets.BeaconPacket(
            from_call=fake.FAKE_FROM_CALLSIGN,
            to_call=fake.FAKE_TO_CALLSIGN,
            latitude=37.7749,
            longitude=-122.4194,
            symbol='>',
            symbol_table='/',
            comment='Test beacon comment',
        )
        json_str = packet.to_json()
        self.assertIsInstance(json_str, str)
        json_dict = json.loads(json_str)
        self.assertEqual(json_dict['_type'], 'BeaconPacket')
        self.assertEqual(json_dict['from_call'], fake.FAKE_FROM_CALLSIGN)
        self.assertEqual(json_dict['to_call'], fake.FAKE_TO_CALLSIGN)
        self.assertEqual(json_dict['latitude'], 37.7749)
        self.assertEqual(json_dict['longitude'], -122.4194)
        self.assertEqual(json_dict['symbol'], '>')
        self.assertEqual(json_dict['symbol_table'], '/')
        self.assertEqual(json_dict['comment'], 'Test beacon comment')

    def test_beacon_packet_from_dict(self):
        """Test BeaconPacket.from_dict() method."""
        packet_dict = {
            '_type': 'BeaconPacket',
            'from_call': fake.FAKE_FROM_CALLSIGN,
            'to_call': fake.FAKE_TO_CALLSIGN,
            'latitude': 37.7749,
            'longitude': -122.4194,
            'symbol': '>',
            'symbol_table': '/',
            'comment': 'Test beacon comment',
        }
        packet = packets.BeaconPacket.from_dict(packet_dict)
        self.assertIsInstance(packet, packets.BeaconPacket)
        self.assertEqual(packet.from_call, fake.FAKE_FROM_CALLSIGN)
        self.assertEqual(packet.to_call, fake.FAKE_TO_CALLSIGN)
        self.assertEqual(packet.latitude, 37.7749)
        self.assertEqual(packet.longitude, -122.4194)
        self.assertEqual(packet.symbol, '>')
        self.assertEqual(packet.symbol_table, '/')
        self.assertEqual(packet.comment, 'Test beacon comment')

    def test_beacon_packet_round_trip(self):
        """Test BeaconPacket round-trip: to_json -> from_dict."""
        original = packets.BeaconPacket(
            from_call=fake.FAKE_FROM_CALLSIGN,
            to_call=fake.FAKE_TO_CALLSIGN,
            latitude=37.7749,
            longitude=-122.4194,
            symbol='>',
            symbol_table='/',
            comment='Test beacon comment',
        )
        json_str = original.to_json()
        packet_dict = json.loads(json_str)
        restored = packets.BeaconPacket.from_dict(packet_dict)
        self.assertEqual(restored.from_call, original.from_call)
        self.assertEqual(restored.to_call, original.to_call)
        self.assertEqual(restored.latitude, original.latitude)
        self.assertEqual(restored.longitude, original.longitude)
        self.assertEqual(restored.symbol, original.symbol)
        self.assertEqual(restored.symbol_table, original.symbol_table)
        self.assertEqual(restored.comment, original.comment)
        self.assertEqual(restored._type, original._type)

    def test_beacon_packet_from_raw_string(self):
        """Test BeaconPacket creation from raw APRS string."""
        # Use a format that aprslib can parse correctly
        packet_raw = 'kd8mey-10>APRS,TCPIP*,qAC,T2SYDNEY:=4247.80N/08539.00WrPHG1210/Making 220 Great Again Allstar# 552191'
        packet_dict = aprslib.parse(packet_raw)
        packet = packets.factory(packet_dict)
        self.assertIsInstance(packet, packets.BeaconPacket)
        # Test to_json
        json_str = packet.to_json()
        self.assertIsInstance(json_str, str)
        json_dict = json.loads(json_str)
        self.assertEqual(json_dict['_type'], 'BeaconPacket')
        # Test from_dict round trip
        restored = packets.factory(json_dict)
        self.assertIsInstance(restored, packets.BeaconPacket)
        self.assertEqual(restored.from_call, packet.from_call)
        self.assertEqual(restored.latitude, packet.latitude)
        self.assertEqual(restored.longitude, packet.longitude)
