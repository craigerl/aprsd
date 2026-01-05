import json
import unittest

import aprslib

from aprsd import packets
from tests import fake


class TestWeatherPacket(unittest.TestCase):
    """Test WeatherPacket JSON serialization."""

    def test_weather_packet_to_json(self):
        """Test WeatherPacket.to_json() method."""
        packet = packets.WeatherPacket(
            from_call=fake.FAKE_FROM_CALLSIGN,
            to_call=fake.FAKE_TO_CALLSIGN,
            latitude=37.7749,
            longitude=-122.4194,
            symbol='_',
            symbol_table='/',
            wind_speed=10.5,
            wind_direction=180,
            wind_gust=15.0,
            temperature=72.5,
            rain_1h=0.1,
            rain_24h=0.5,
            rain_since_midnight=0.3,
            humidity=65,
            pressure=1013.25,
            comment='Test weather comment',
        )
        json_str = packet.to_json()
        self.assertIsInstance(json_str, str)
        json_dict = json.loads(json_str)
        self.assertEqual(json_dict['_type'], 'WeatherPacket')
        self.assertEqual(json_dict['from_call'], fake.FAKE_FROM_CALLSIGN)
        self.assertEqual(json_dict['to_call'], fake.FAKE_TO_CALLSIGN)
        self.assertEqual(json_dict['latitude'], 37.7749)
        self.assertEqual(json_dict['longitude'], -122.4194)
        self.assertEqual(json_dict['symbol'], '_')
        self.assertEqual(json_dict['wind_speed'], 10.5)
        self.assertEqual(json_dict['wind_direction'], 180)
        self.assertEqual(json_dict['wind_gust'], 15.0)
        self.assertEqual(json_dict['temperature'], 72.5)
        self.assertEqual(json_dict['rain_1h'], 0.1)
        self.assertEqual(json_dict['rain_24h'], 0.5)
        self.assertEqual(json_dict['rain_since_midnight'], 0.3)
        self.assertEqual(json_dict['humidity'], 65)
        self.assertEqual(json_dict['pressure'], 1013.25)
        self.assertEqual(json_dict['comment'], 'Test weather comment')

    def test_weather_packet_from_dict(self):
        """Test WeatherPacket.from_dict() method."""
        packet_dict = {
            '_type': 'WeatherPacket',
            'from_call': fake.FAKE_FROM_CALLSIGN,
            'to_call': fake.FAKE_TO_CALLSIGN,
            'latitude': 37.7749,
            'longitude': -122.4194,
            'symbol': '_',
            'symbol_table': '/',
            'wind_speed': 10.5,
            'wind_direction': 180,
            'wind_gust': 15.0,
            'temperature': 72.5,
            'rain_1h': 0.1,
            'rain_24h': 0.5,
            'rain_since_midnight': 0.3,
            'humidity': 65,
            'pressure': 1013.25,
            'comment': 'Test weather comment',
        }
        packet = packets.WeatherPacket.from_dict(packet_dict)
        self.assertIsInstance(packet, packets.WeatherPacket)
        self.assertEqual(packet.from_call, fake.FAKE_FROM_CALLSIGN)
        self.assertEqual(packet.to_call, fake.FAKE_TO_CALLSIGN)
        self.assertEqual(packet.latitude, 37.7749)
        self.assertEqual(packet.longitude, -122.4194)
        self.assertEqual(packet.symbol, '_')
        self.assertEqual(packet.wind_speed, 10.5)
        self.assertEqual(packet.wind_direction, 180)
        self.assertEqual(packet.wind_gust, 15.0)
        self.assertEqual(packet.temperature, 72.5)
        self.assertEqual(packet.rain_1h, 0.1)
        self.assertEqual(packet.rain_24h, 0.5)
        self.assertEqual(packet.rain_since_midnight, 0.3)
        self.assertEqual(packet.humidity, 65)
        self.assertEqual(packet.pressure, 1013.25)
        self.assertEqual(packet.comment, 'Test weather comment')

    def test_weather_packet_round_trip(self):
        """Test WeatherPacket round-trip: to_json -> from_dict."""
        original = packets.WeatherPacket(
            from_call=fake.FAKE_FROM_CALLSIGN,
            to_call=fake.FAKE_TO_CALLSIGN,
            latitude=37.7749,
            longitude=-122.4194,
            symbol='_',
            symbol_table='/',
            wind_speed=10.5,
            wind_direction=180,
            wind_gust=15.0,
            temperature=72.5,
            rain_1h=0.1,
            rain_24h=0.5,
            rain_since_midnight=0.3,
            humidity=65,
            pressure=1013.25,
            comment='Test weather comment',
        )
        json_str = original.to_json()
        packet_dict = json.loads(json_str)
        restored = packets.WeatherPacket.from_dict(packet_dict)
        self.assertEqual(restored.from_call, original.from_call)
        self.assertEqual(restored.to_call, original.to_call)
        self.assertEqual(restored.latitude, original.latitude)
        self.assertEqual(restored.longitude, original.longitude)
        self.assertEqual(restored.symbol, original.symbol)
        self.assertEqual(restored.wind_speed, original.wind_speed)
        self.assertEqual(restored.wind_direction, original.wind_direction)
        self.assertEqual(restored.wind_gust, original.wind_gust)
        self.assertEqual(restored.temperature, original.temperature)
        self.assertEqual(restored.rain_1h, original.rain_1h)
        self.assertEqual(restored.rain_24h, original.rain_24h)
        self.assertEqual(restored.rain_since_midnight, original.rain_since_midnight)
        self.assertEqual(restored.humidity, original.humidity)
        self.assertEqual(restored.pressure, original.pressure)
        self.assertEqual(restored.comment, original.comment)
        self.assertEqual(restored._type, original._type)

    def test_weather_packet_from_raw_string(self):
        """Test WeatherPacket creation from raw APRS string."""
        packet_raw = 'FW9222>APRS,TCPXX*,qAX,CWOP-6:@122025z2953.94N/08423.77W_232/003g006t084r000p032P000h80b10157L745.DsWLL'
        packet_dict = aprslib.parse(packet_raw)
        packet = packets.factory(packet_dict)
        self.assertIsInstance(packet, packets.WeatherPacket)
        # Test to_json
        json_str = packet.to_json()
        self.assertIsInstance(json_str, str)
        json_dict = json.loads(json_str)
        self.assertEqual(json_dict['_type'], 'WeatherPacket')
        # Test from_dict round trip
        restored = packets.factory(json_dict)
        self.assertIsInstance(restored, packets.WeatherPacket)
        self.assertEqual(restored.from_call, packet.from_call)
        self.assertEqual(restored.temperature, packet.temperature)
        self.assertEqual(restored.humidity, packet.humidity)
        self.assertEqual(restored.pressure, packet.pressure)
        self.assertEqual(restored.wind_speed, packet.wind_speed)
        self.assertEqual(restored.wind_direction, packet.wind_direction)
