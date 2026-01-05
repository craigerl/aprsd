import json
import unittest

import aprslib

from aprsd import packets
from tests import fake


class TestMicEPacket(unittest.TestCase):
    """Test MicEPacket JSON serialization."""

    def test_mice_packet_to_json(self):
        """Test MicEPacket.to_json() method."""
        packet = packets.MicEPacket(
            from_call=fake.FAKE_FROM_CALLSIGN,
            to_call=fake.FAKE_TO_CALLSIGN,
            latitude=37.7749,
            longitude=-122.4194,
            speed=25.5,
            course=180,
            mbits='test',
            mtype='test_type',
            telemetry={'key': 'value'},
        )
        json_str = packet.to_json()
        self.assertIsInstance(json_str, str)
        json_dict = json.loads(json_str)
        self.assertEqual(json_dict['_type'], 'MicEPacket')
        self.assertEqual(json_dict['from_call'], fake.FAKE_FROM_CALLSIGN)
        self.assertEqual(json_dict['to_call'], fake.FAKE_TO_CALLSIGN)
        self.assertEqual(json_dict['latitude'], 37.7749)
        self.assertEqual(json_dict['longitude'], -122.4194)
        self.assertEqual(json_dict['speed'], 25.5)
        self.assertEqual(json_dict['course'], 180)
        self.assertEqual(json_dict['mbits'], 'test')
        self.assertEqual(json_dict['mtype'], 'test_type')

    def test_mice_packet_from_dict(self):
        """Test MicEPacket.from_dict() method."""
        packet_dict = {
            '_type': 'MicEPacket',
            'from_call': fake.FAKE_FROM_CALLSIGN,
            'to_call': fake.FAKE_TO_CALLSIGN,
            'latitude': 37.7749,
            'longitude': -122.4194,
            'speed': 25.5,
            'course': 180,
            'mbits': 'test',
            'mtype': 'test_type',
            'telemetry': {'key': 'value'},
        }
        packet = packets.MicEPacket.from_dict(packet_dict)
        self.assertIsInstance(packet, packets.MicEPacket)
        self.assertEqual(packet.from_call, fake.FAKE_FROM_CALLSIGN)
        self.assertEqual(packet.to_call, fake.FAKE_TO_CALLSIGN)
        self.assertEqual(packet.latitude, 37.7749)
        self.assertEqual(packet.longitude, -122.4194)
        self.assertEqual(packet.speed, 25.5)
        self.assertEqual(packet.course, 180)
        self.assertEqual(packet.mbits, 'test')
        self.assertEqual(packet.mtype, 'test_type')

    def test_mice_packet_round_trip(self):
        """Test MicEPacket round-trip: to_json -> from_dict."""
        original = packets.MicEPacket(
            from_call=fake.FAKE_FROM_CALLSIGN,
            to_call=fake.FAKE_TO_CALLSIGN,
            latitude=37.7749,
            longitude=-122.4194,
            speed=25.5,
            course=180,
            mbits='test',
            mtype='test_type',
            telemetry={'key': 'value'},
        )
        json_str = original.to_json()
        packet_dict = json.loads(json_str)
        restored = packets.MicEPacket.from_dict(packet_dict)
        self.assertEqual(restored.from_call, original.from_call)
        self.assertEqual(restored.to_call, original.to_call)
        self.assertEqual(restored.latitude, original.latitude)
        self.assertEqual(restored.longitude, original.longitude)
        self.assertEqual(restored.speed, original.speed)
        self.assertEqual(restored.course, original.course)
        self.assertEqual(restored.mbits, original.mbits)
        self.assertEqual(restored.mtype, original.mtype)
        self.assertEqual(restored._type, original._type)

    def test_mice_packet_from_raw_string(self):
        """Test MicEPacket creation from raw APRS string."""
        packet_raw = 'kh2sr-15>S7TSYR,WIDE1-1,WIDE2-1,qAO,KO6KL-1:`1`7\x1c\x1c.#/`"4,}QuirkyQRP 4.6V  35.3C S06'
        packet_dict = aprslib.parse(packet_raw)
        packet = packets.factory(packet_dict)
        self.assertIsInstance(packet, packets.MicEPacket)
        # Test to_json
        json_str = packet.to_json()
        self.assertIsInstance(json_str, str)
        json_dict = json.loads(json_str)
        self.assertEqual(json_dict['_type'], 'MicEPacket')
        # Test from_dict round trip
        restored = packets.factory(json_dict)
        self.assertIsInstance(restored, packets.MicEPacket)
        self.assertEqual(restored.from_call, packet.from_call)
        if hasattr(packet, 'latitude') and packet.latitude:
            self.assertEqual(restored.latitude, packet.latitude)
            self.assertEqual(restored.longitude, packet.longitude)
