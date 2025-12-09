import datetime
import decimal
import json
import unittest

from aprsd.utils.json import EnhancedJSONDecoder, EnhancedJSONEncoder, SimpleJSONEncoder
from tests import fake


class TestEnhancedJSONEncoder(unittest.TestCase):
    """Unit tests for the EnhancedJSONEncoder class."""

    def test_encode_datetime(self):
        """Test encoding datetime objects."""
        dt = datetime.datetime(2023, 1, 15, 10, 30, 45, 123456)
        encoder = EnhancedJSONEncoder()

        result = encoder.default(dt)
        self.assertEqual(result['__type__'], 'datetime.datetime')
        self.assertIn('args', result)
        self.assertEqual(result['args'][0], 2023)  # year
        self.assertEqual(result['args'][1], 1)  # month

    def test_encode_date(self):
        """Test encoding date objects."""
        d = datetime.date(2023, 1, 15)
        encoder = EnhancedJSONEncoder()

        result = encoder.default(d)
        self.assertEqual(result['__type__'], 'datetime.date')
        self.assertIn('args', result)
        self.assertEqual(result['args'][0], 2023)

    def test_encode_time(self):
        """Test encoding time objects."""
        t = datetime.time(10, 30, 45, 123456)
        encoder = EnhancedJSONEncoder()

        result = encoder.default(t)
        self.assertEqual(result['__type__'], 'datetime.time')
        self.assertIn('args', result)
        self.assertEqual(result['args'][0], 10)  # hour

    def test_encode_timedelta(self):
        """Test encoding timedelta objects."""
        td = datetime.timedelta(days=1, seconds=3600, microseconds=500000)
        encoder = EnhancedJSONEncoder()

        result = encoder.default(td)
        self.assertEqual(result['__type__'], 'datetime.timedelta')
        self.assertIn('args', result)
        self.assertEqual(result['args'][0], 1)  # days

    def test_encode_decimal(self):
        """Test encoding Decimal objects."""
        dec = decimal.Decimal('123.456')
        encoder = EnhancedJSONEncoder()

        result = encoder.default(dec)
        self.assertEqual(result['__type__'], 'decimal.Decimal')
        self.assertIn('args', result)
        self.assertEqual(result['args'][0], '123.456')

    def test_encode_unknown(self):
        """Test encoding unknown objects falls back to super."""
        encoder = EnhancedJSONEncoder()

        with self.assertRaises(TypeError):
            encoder.default(object())


class TestSimpleJSONEncoder(unittest.TestCase):
    """Unit tests for the SimpleJSONEncoder class."""

    def test_encode_datetime(self):
        """Test encoding datetime objects."""
        dt = datetime.datetime(2023, 1, 15, 10, 30, 45)
        encoder = SimpleJSONEncoder()

        result = encoder.default(dt)
        self.assertIsInstance(result, str)
        self.assertIn('2023', result)

    def test_encode_date(self):
        """Test encoding date objects."""
        d = datetime.date(2023, 1, 15)
        encoder = SimpleJSONEncoder()

        result = encoder.default(d)
        self.assertIsInstance(result, str)
        self.assertIn('2023', result)

    def test_encode_time(self):
        """Test encoding time objects."""
        t = datetime.time(10, 30, 45)
        encoder = SimpleJSONEncoder()

        result = encoder.default(t)
        self.assertIsInstance(result, str)

    def test_encode_timedelta(self):
        """Test encoding timedelta objects."""
        td = datetime.timedelta(days=1, seconds=3600)
        encoder = SimpleJSONEncoder()

        result = encoder.default(td)
        self.assertIsInstance(result, str)

    def test_encode_decimal(self):
        """Test encoding Decimal objects."""
        dec = decimal.Decimal('123.456')
        encoder = SimpleJSONEncoder()

        result = encoder.default(dec)
        self.assertEqual(result, '123.456')

    def test_encode_packet(self):
        """Test encoding Packet objects."""
        packet = fake.fake_packet()
        encoder = SimpleJSONEncoder()

        result = encoder.default(packet)
        self.assertIsInstance(result, dict)
        # Should have packet attributes
        self.assertIn('from_call', result)

    def test_encode_unknown(self):
        """Test encoding unknown objects falls back to super."""
        encoder = SimpleJSONEncoder()

        with self.assertRaises(TypeError):
            encoder.default(object())


class TestEnhancedJSONDecoder(unittest.TestCase):
    """Unit tests for the EnhancedJSONDecoder class."""

    def test_decode_datetime(self):
        """Test decoding datetime objects."""
        dt = datetime.datetime(2023, 1, 15, 10, 30, 45, 123456)
        encoder = EnhancedJSONEncoder()

        encoded = encoder.default(dt)
        json_str = json.dumps(encoded)
        decoded = json.loads(json_str, cls=EnhancedJSONDecoder)

        self.assertIsInstance(decoded, datetime.datetime)
        self.assertEqual(decoded.year, 2023)
        self.assertEqual(decoded.month, 1)

    def test_decode_date(self):
        """Test decoding date objects."""
        d = datetime.date(2023, 1, 15)
        encoder = EnhancedJSONEncoder()

        encoded = encoder.default(d)
        json_str = json.dumps(encoded)
        decoded = json.loads(json_str, cls=EnhancedJSONDecoder)

        self.assertIsInstance(decoded, datetime.date)
        self.assertEqual(decoded.year, 2023)

    def test_decode_time(self):
        """Test decoding time objects."""
        t = datetime.time(10, 30, 45, 123456)
        encoder = EnhancedJSONEncoder()

        encoded = encoder.default(t)
        json_str = json.dumps(encoded)
        decoded = json.loads(json_str, cls=EnhancedJSONDecoder)

        self.assertIsInstance(decoded, datetime.time)
        self.assertEqual(decoded.hour, 10)

    def test_decode_timedelta(self):
        """Test decoding timedelta objects."""
        td = datetime.timedelta(days=1, seconds=3600, microseconds=500000)
        encoder = EnhancedJSONEncoder()

        encoded = encoder.default(td)
        json_str = json.dumps(encoded)
        decoded = json.loads(json_str, cls=EnhancedJSONDecoder)

        self.assertIsInstance(decoded, datetime.timedelta)
        self.assertEqual(decoded.days, 1)

    def test_decode_decimal(self):
        """Test decoding Decimal objects."""
        dec = decimal.Decimal('123.456')
        encoder = EnhancedJSONEncoder()

        encoded = encoder.default(dec)
        json_str = json.dumps(encoded)
        decoded = json.loads(json_str, cls=EnhancedJSONDecoder)

        self.assertIsInstance(decoded, decimal.Decimal)
        self.assertEqual(str(decoded), '123.456')

    def test_decode_normal_dict(self):
        """Test decoding normal dictionaries."""
        normal_dict = {'key': 'value', 'number': 42}
        json_str = json.dumps(normal_dict)
        decoded = json.loads(json_str, cls=EnhancedJSONDecoder)

        self.assertEqual(decoded, normal_dict)

    def test_object_hook_no_type(self):
        """Test object_hook with dict without __type__."""
        decoder = EnhancedJSONDecoder()
        normal_dict = {'key': 'value'}

        result = decoder.object_hook(normal_dict)
        self.assertEqual(result, normal_dict)
