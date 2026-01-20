import json
import unittest

import aprslib

from aprsd import packets
from aprsd.packets.core import TelemetryPacket
from tests import fake


class TestTelemetryPacket(unittest.TestCase):
    """Test TelemetryPacket JSON serialization."""

    def test_telemetry_packet_to_json(self):
        """Test TelemetryPacket.to_json() method."""
        packet = TelemetryPacket(
            from_call=fake.FAKE_FROM_CALLSIGN,
            to_call=fake.FAKE_TO_CALLSIGN,
            latitude=37.7749,
            longitude=-122.4194,
            speed=25.5,
            course=180,
            mbits='test',
            mtype='test_type',
            telemetry={'key': 'value'},
            tPARM=['parm1', 'parm2'],
            tUNIT=['unit1', 'unit2'],
        )
        json_str = packet.to_json()
        self.assertIsInstance(json_str, str)
        json_dict = json.loads(json_str)
        self.assertEqual(json_dict['_type'], 'TelemetryPacket')
        self.assertEqual(json_dict['from_call'], fake.FAKE_FROM_CALLSIGN)
        self.assertEqual(json_dict['to_call'], fake.FAKE_TO_CALLSIGN)
        self.assertEqual(json_dict['latitude'], 37.7749)
        self.assertEqual(json_dict['longitude'], -122.4194)
        self.assertEqual(json_dict['speed'], 25.5)
        self.assertEqual(json_dict['course'], 180)
        self.assertEqual(json_dict['mbits'], 'test')
        self.assertEqual(json_dict['mtype'], 'test_type')

    def test_telemetry_packet_from_dict(self):
        """Test TelemetryPacket.from_dict() method."""
        packet_dict = {
            '_type': 'TelemetryPacket',
            'from_call': fake.FAKE_FROM_CALLSIGN,
            'to_call': fake.FAKE_TO_CALLSIGN,
            'latitude': 37.7749,
            'longitude': -122.4194,
            'speed': 25.5,
            'course': 180,
            'mbits': 'test',
            'mtype': 'test_type',
            'telemetry': {'key': 'value'},
            'tPARM': ['parm1', 'parm2'],
            'tUNIT': ['unit1', 'unit2'],
        }
        packet = TelemetryPacket.from_dict(packet_dict)
        self.assertIsInstance(packet, TelemetryPacket)
        self.assertEqual(packet.from_call, fake.FAKE_FROM_CALLSIGN)
        self.assertEqual(packet.to_call, fake.FAKE_TO_CALLSIGN)
        self.assertEqual(packet.latitude, 37.7749)
        self.assertEqual(packet.longitude, -122.4194)
        self.assertEqual(packet.speed, 25.5)
        self.assertEqual(packet.course, 180)
        self.assertEqual(packet.mbits, 'test')
        self.assertEqual(packet.mtype, 'test_type')

    def test_telemetry_packet_round_trip(self):
        """Test TelemetryPacket round-trip: to_json -> from_dict."""
        original = TelemetryPacket(
            from_call=fake.FAKE_FROM_CALLSIGN,
            to_call=fake.FAKE_TO_CALLSIGN,
            latitude=37.7749,
            longitude=-122.4194,
            speed=25.5,
            course=180,
            mbits='test',
            mtype='test_type',
            telemetry={'key': 'value'},
            tPARM=['parm1', 'parm2'],
            tUNIT=['unit1', 'unit2'],
        )
        json_str = original.to_json()
        packet_dict = json.loads(json_str)
        restored = TelemetryPacket.from_dict(packet_dict)
        self.assertEqual(restored.from_call, original.from_call)
        self.assertEqual(restored.to_call, original.to_call)
        self.assertEqual(restored.latitude, original.latitude)
        self.assertEqual(restored.longitude, original.longitude)
        self.assertEqual(restored.speed, original.speed)
        self.assertEqual(restored.course, original.course)
        self.assertEqual(restored.mbits, original.mbits)
        self.assertEqual(restored.mtype, original.mtype)
        self.assertEqual(restored._type, original._type)

    def test_telemetry_packet_from_raw_string(self):
        """Test TelemetryPacket creation from raw APRS string."""
        # Telemetry packets are less common, using a Mic-E with telemetry as example
        packet_raw = (
            "KD9YIL>T0PX9W,WIDE1-1,WIDE2-1,qAO,NU9R-10:`sB,l#P>/'\"6+}|#*%U'a|!whl!|3"
        )
        packet_dict = aprslib.parse(packet_raw)
        packet = packets.factory(packet_dict)
        # This might be MicEPacket or TelemetryPacket depending on content
        self.assertIsNotNone(packet)
        # Test to_json
        json_str = packet.to_json()
        self.assertIsInstance(json_str, str)
        json_dict = json.loads(json_str)
        # Test from_dict round trip
        restored = packets.factory(json_dict)
        self.assertEqual(restored.from_call, packet.from_call)
        if hasattr(packet, 'telemetry') and packet.telemetry:
            self.assertIsNotNone(restored.telemetry)
