import json
import unittest
import warnings

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
            position=packets.Position(
                latitude=37.7749,
                longitude=-122.4194,
                altitude=100.0,
                symbol='>',
                symbol_table='/',
                comment='Test GPS comment',
            ),
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
        self.assertEqual(packet.position.latitude, 37.7749)
        self.assertEqual(packet.position.longitude, -122.4194)
        self.assertEqual(packet.position.altitude, 100.0)
        self.assertEqual(packet.position.symbol, '>')
        self.assertEqual(packet.position.symbol_table, '/')
        self.assertEqual(packet.position.comment, 'Test GPS comment')

    def test_gps_packet_round_trip(self):
        """Test GPSPacket round-trip: to_json -> from_dict."""
        original = packets.GPSPacket(
            from_call=fake.FAKE_FROM_CALLSIGN,
            to_call=fake.FAKE_TO_CALLSIGN,
            position=packets.Position(
                latitude=37.7749,
                longitude=-122.4194,
                altitude=100.0,
                symbol='>',
                symbol_table='/',
                comment='Test GPS comment',
                speed=25.5,
                course=180,
            ),
        )

        json_str = original.to_json()
        packet_dict = json.loads(json_str)
        restored = packets.GPSPacket.from_dict(packet_dict)
        self.assertEqual(restored.from_call, original.from_call)
        self.assertEqual(restored.to_call, original.to_call)
        self.assertEqual(restored.position.latitude, original.position.latitude)
        self.assertEqual(restored.position.longitude, original.position.longitude)
        self.assertEqual(restored.position.altitude, original.position.altitude)
        self.assertEqual(restored.position.symbol, original.position.symbol)
        self.assertEqual(restored.position.symbol_table, original.position.symbol_table)
        self.assertEqual(restored.position.comment, original.position.comment)
        self.assertEqual(restored.position.speed, original.position.speed)
        self.assertEqual(restored.position.course, original.position.course)
        self.assertEqual(restored._type, original._type)

    def test_gps_packet_from_raw_string(self):
        """Test GPSPacket creation from raw APRS string."""
        packet_raw = 'KFAKE>APZ100,WIDE2-1:!3742.00N/12225.00W>Test GPS comment'
        packet_dict = aprslib.parse(packet_raw)
        packet = packets.factory(packet_dict)
        # GPS packets are typically created as BeaconPacket or other types
        # but we can test if it has GPS data
        self.assertIsNotNone(packet)
        if packet.position is not None:
            # Test to_json
            json_str = packet.to_json()
            self.assertIsInstance(json_str, str)
            json_dict = json.loads(json_str)
            self.assertIn('latitude', json_dict)
            self.assertIn('longitude', json_dict)
            # Test from_dict round trip
            restored = packets.factory(json_dict)
            self.assertEqual(restored.position.latitude, packet.position.latitude)
            self.assertEqual(restored.position.longitude, packet.position.longitude)


class TestGPSPacketBackwardCompat(unittest.TestCase):
    """Backward-compat shim: legacy flat position kwargs + flat attr reads.

    The GPS packet types accept BOTH position=Position(...) (canonical) and
    the legacy flat keyword arguments (latitude=, longitude=, symbol=, ...),
    which emit a DeprecationWarning.  Flat attribute reads (packet.latitude)
    also keep working.  These are temporary shims to avoid breaking external
    plugins/extensions and are scheduled for removal.
    """

    def _assert_no_deprecation(self, fn):
        with warnings.catch_warnings():
            warnings.simplefilter('error', DeprecationWarning)
            fn()

    def test_flat_kwargs_deprecated(self):
        """Legacy flat kwargs still construct a packet, with a warning."""
        with self.assertWarns(DeprecationWarning):
            pkt = packets.BeaconPacket(
                from_call=fake.FAKE_FROM_CALLSIGN,
                to_call=fake.FAKE_TO_CALLSIGN,
                latitude=37.7749,
                longitude=-122.4194,
                symbol='>',
                comment='Test beacon comment',
            )
        self.assertIsNotNone(pkt.position)
        self.assertEqual(37.7749, pkt.position.latitude)
        self.assertEqual(-122.4194, pkt.position.longitude)
        self.assertEqual('>', pkt.position.symbol)
        self.assertEqual('Test beacon comment', pkt.position.comment)

    def test_flat_kwargs_preserve_per_type_symbol(self):
        """Legacy flat kwargs keep the per-type symbol defaults (r/_/l)."""
        with self.assertWarns(DeprecationWarning):
            obj = packets.ObjectPacket(
                from_call='KFAKE', to_call='KMINE', latitude=1.0, longitude=2.0
            )
        self.assertEqual('r', obj.position.symbol)
        with self.assertWarns(DeprecationWarning):
            wx = packets.WeatherPacket(
                from_call='KFAKE', to_call='KMINE', latitude=1.0, longitude=2.0
            )
        self.assertEqual('_', wx.position.symbol)
        with self.assertWarns(DeprecationWarning):
            gps = packets.GPSPacket(
                from_call='KFAKE', to_call='KMINE', latitude=1.0, longitude=2.0
            )
        self.assertEqual('l', gps.position.symbol)

    def test_flat_attribute_reads(self):
        """packet.latitude and friends still work as read-only attributes."""
        pkt = packets.GPSPacket(
            from_call='KFAKE',
            to_call='KMINE',
            position=packets.Position(
                latitude=37.7749,
                longitude=-122.4194,
                altitude=100.0,
                symbol='>',
                comment='c',
                speed=25.5,
                course=180,
            ),
        )
        self.assertEqual(37.7749, pkt.latitude)
        self.assertEqual(-122.4194, pkt.longitude)
        self.assertEqual(100.0, pkt.altitude)
        self.assertEqual('>', pkt.symbol)
        self.assertEqual('c', pkt.comment)
        self.assertEqual(25.5, pkt.speed)
        self.assertEqual(180, pkt.course)

    def test_position_kwarg_no_deprecation(self):
        """The canonical position= form must not emit a warning."""
        self._assert_no_deprecation(
            lambda: packets.BeaconPacket(
                from_call='KFAKE',
                to_call='KMINE',
                position=packets.Position(latitude=1.0, longitude=2.0),
            )
        )

    def test_both_kwargs_raises(self):
        """Passing position= AND flat kwargs is ambiguous and must fail."""
        with self.assertRaises(TypeError):
            packets.BeaconPacket(
                from_call='KFAKE',
                to_call='KMINE',
                position=packets.Position(latitude=1.0, longitude=2.0),
                latitude=1.0,
            )

    def test_positional_args_raises(self):
        """GPS packet types only accept keyword arguments."""
        with self.assertRaises(TypeError):
            packets.BeaconPacket('KFAKE')

    def test_flat_and_position_constructors_equal(self):
        """A legacy flat-kwarg packet equals its position= equivalent."""
        with self.assertWarns(DeprecationWarning):
            flat = packets.ObjectPacket(
                from_call='KFAKE',
                to_call='KMINE',
                latitude=1.0,
                longitude=2.0,
                comment='c',
            )
        pos = packets.ObjectPacket(
            from_call='KFAKE',
            to_call='KMINE',
            position=packets.Position(
                latitude=1.0, longitude=2.0, comment='c', symbol='r'
            ),
        )
        self.assertEqual(flat, pos)
