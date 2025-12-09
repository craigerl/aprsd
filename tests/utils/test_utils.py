import os
import shutil
import tempfile
import unittest
from unittest import mock

from aprsd import utils


class TestUtils(unittest.TestCase):
    """Unit tests for utility functions in aprsd.utils."""

    def test_singleton_decorator(self):
        """Test singleton() decorator."""

        @utils.singleton
        class TestClass:
            def __init__(self):
                self.value = 42

        instance1 = TestClass()
        instance2 = TestClass()

        self.assertIs(instance1, instance2)
        self.assertEqual(instance1.value, 42)

    def test_env(self):
        """Test env() function."""
        # Test with existing environment variable
        os.environ['TEST_VAR'] = 'test_value'
        result = utils.env('TEST_VAR')
        self.assertEqual(result, 'test_value')

        # Test with non-existent variable
        result = utils.env('NON_EXISTENT_VAR')
        self.assertEqual(result, '')

        # Test with default
        result = utils.env('NON_EXISTENT_VAR2', default='default_value')
        self.assertEqual(result, 'default_value')

        # Cleanup
        del os.environ['TEST_VAR']

    def test_env_multiple_vars(self):
        """Test env() with multiple variables."""
        os.environ['VAR1'] = 'value1'
        result = utils.env('VAR1', 'VAR2', 'VAR3')
        self.assertEqual(result, 'value1')

        del os.environ['VAR1']

    def test_mkdir_p(self):
        """Test mkdir_p() function."""
        temp_dir = tempfile.mkdtemp()
        test_path = os.path.join(temp_dir, 'test', 'nested', 'dir')

        try:
            utils.mkdir_p(test_path)
            self.assertTrue(os.path.isdir(test_path))

            # Should not raise exception if directory exists
            utils.mkdir_p(test_path)
            self.assertTrue(os.path.isdir(test_path))
        finally:
            shutil.rmtree(temp_dir)

    def test_insert_str(self):
        """Test insert_str() function."""
        result = utils.insert_str('hello', ' world', 5)
        self.assertEqual(result, 'hello world')

        result = utils.insert_str('test', 'X', 0)
        self.assertEqual(result, 'Xtest')

        result = utils.insert_str('test', 'X', 4)
        self.assertEqual(result, 'testX')

    def test_end_substr(self):
        """Test end_substr() function."""
        result = utils.end_substr('hello world', 'hello')
        self.assertEqual(result, 5)

        result = utils.end_substr('test', 'notfound')
        self.assertEqual(result, -1)

        result = utils.end_substr('abc', 'abc')
        self.assertEqual(result, 3)

    def test_rgb_from_name(self):
        """Test rgb_from_name() function."""
        rgb = utils.rgb_from_name('test')
        self.assertIsInstance(rgb, tuple)
        self.assertEqual(len(rgb), 3)
        self.assertGreaterEqual(rgb[0], 0)
        self.assertLessEqual(rgb[0], 255)
        self.assertGreaterEqual(rgb[1], 0)
        self.assertLessEqual(rgb[1], 255)
        self.assertGreaterEqual(rgb[2], 0)
        self.assertLessEqual(rgb[2], 255)

        # Same name should produce same RGB
        rgb1 = utils.rgb_from_name('test')
        rgb2 = utils.rgb_from_name('test')
        self.assertEqual(rgb1, rgb2)

    def test_hextriplet(self):
        """Test hextriplet() function."""
        result = utils.hextriplet((255, 0, 128))
        self.assertEqual(result, '#FF0080')

        result = utils.hextriplet((0, 0, 0))
        self.assertEqual(result, '#000000')

        result = utils.hextriplet((255, 255, 255))
        self.assertEqual(result, '#FFFFFF')

    def test_hex_from_name(self):
        """Test hex_from_name() function."""
        hex_color = utils.hex_from_name('test')
        self.assertIsInstance(hex_color, str)
        self.assertTrue(hex_color.startswith('#'))
        self.assertEqual(len(hex_color), 7)

        # Same name should produce same hex
        hex1 = utils.hex_from_name('test')
        hex2 = utils.hex_from_name('test')
        self.assertEqual(hex1, hex2)

    def test_human_size(self):
        """Test human_size() function."""
        result = utils.human_size(1024)
        self.assertIn('KB', result)

        result = utils.human_size(512)
        self.assertIn('bytes', result)

        result = utils.human_size(1024 * 1024)
        self.assertIn('MB', result)

    def test_strfdelta(self):
        """Test strfdelta() function."""
        import datetime

        delta = datetime.timedelta(hours=1, minutes=30, seconds=45)
        result = utils.strfdelta(delta)
        self.assertIn('01', result)
        self.assertIn('30', result)
        self.assertIn('45', result)

        delta = datetime.timedelta(days=1, hours=2, minutes=30, seconds=15)
        result = utils.strfdelta(delta)
        self.assertIn('1 days', result)

    def test_flatten_dict(self):
        """Test flatten_dict() function."""
        nested = {'a': 1, 'b': {'c': 2, 'd': {'e': 3}}}
        result = utils.flatten_dict(nested)
        self.assertIn('a', result)
        self.assertIn('b.c', result)
        self.assertIn('b.d.e', result)
        self.assertEqual(result['a'], 1)
        self.assertEqual(result['b.c'], 2)
        self.assertEqual(result['b.d.e'], 3)

    def test_flatten_dict_custom_sep(self):
        """Test flatten_dict() with custom separator."""
        nested = {'a': {'b': 1}}
        result = utils.flatten_dict(nested, sep='_')
        self.assertIn('a_b', result)

    def test_parse_delta_str(self):
        """Test parse_delta_str() function."""
        result = utils.parse_delta_str('1:30:45')
        self.assertIn('hours', result)
        self.assertIn('minutes', result)
        self.assertIn('seconds', result)
        self.assertEqual(result['hours'], 1.0)
        self.assertEqual(result['minutes'], 30.0)
        self.assertEqual(result['seconds'], 45.0)

        result = utils.parse_delta_str('1 day, 2:30:15')
        self.assertIn('days', result)
        self.assertEqual(result['days'], 1.0)

    def test_parse_delta_str_invalid(self):
        """Test parse_delta_str() with invalid input."""
        result = utils.parse_delta_str('invalid')
        self.assertEqual(result, {})

    def test_calculate_initial_compass_bearing(self):
        """Test calculate_initial_compass_bearing() function."""
        point_a = (40.7128, -74.0060)  # New York
        point_b = (34.0522, -118.2437)  # Los Angeles

        bearing = utils.calculate_initial_compass_bearing(point_a, point_b)
        self.assertGreaterEqual(bearing, 0)
        self.assertLessEqual(bearing, 360)

        # Same point should have undefined bearing, but function should handle it
        bearing = utils.calculate_initial_compass_bearing(point_a, point_a)
        self.assertIsInstance(bearing, float)

    def test_calculate_initial_compass_bearing_invalid(self):
        """Test calculate_initial_compass_bearing() with invalid input."""
        with self.assertRaises(TypeError):
            utils.calculate_initial_compass_bearing([1, 2], (3, 4))

    def test_degrees_to_cardinal(self):
        """Test degrees_to_cardinal() function."""
        self.assertEqual(utils.degrees_to_cardinal(0), 'N')
        self.assertEqual(utils.degrees_to_cardinal(90), 'E')
        self.assertEqual(utils.degrees_to_cardinal(180), 'S')
        self.assertEqual(utils.degrees_to_cardinal(270), 'W')
        self.assertEqual(utils.degrees_to_cardinal(45), 'NE')

    def test_degrees_to_cardinal_full_string(self):
        """Test degrees_to_cardinal() with full_string=True."""
        self.assertEqual(utils.degrees_to_cardinal(0, full_string=True), 'North')
        self.assertEqual(utils.degrees_to_cardinal(90, full_string=True), 'East')
        self.assertEqual(utils.degrees_to_cardinal(180, full_string=True), 'South')
        self.assertEqual(utils.degrees_to_cardinal(270, full_string=True), 'West')

    def test_aprs_passcode(self):
        """Test aprs_passcode() function."""
        passcode = utils.aprs_passcode('N0CALL')
        self.assertIsInstance(passcode, int)
        self.assertGreaterEqual(passcode, 0)
        self.assertLessEqual(passcode, 0x7FFF)

        # Same callsign should produce same passcode
        passcode1 = utils.aprs_passcode('N0CALL')
        passcode2 = utils.aprs_passcode('N0CALL')
        self.assertEqual(passcode1, passcode2)

        # Different callsigns should produce different passcodes
        passcode3 = utils.aprs_passcode('K1ABC')
        self.assertNotEqual(passcode1, passcode3)

    def test_aprs_passcode_with_ssid(self):
        """Test aprs_passcode() with SSID."""
        passcode1 = utils.aprs_passcode('N0CALL-1')
        passcode2 = utils.aprs_passcode('N0CALL')
        self.assertEqual(passcode1, passcode2)

    def test_load_entry_points(self):
        """Test load_entry_points() function."""
        # Should not raise exception even with non-existent group
        utils.load_entry_points('nonexistent.group')

    @mock.patch('aprsd.utils.update_checker.UpdateChecker')
    def test_check_version(self, mock_checker):
        """Test _check_version() function."""
        mock_instance = mock.MagicMock()
        mock_instance.check.return_value = None
        mock_checker.return_value = mock_instance

        level, msg = utils._check_version()
        self.assertEqual(level, 0)
        self.assertIn('up to date', msg)

    @mock.patch('aprsd.utils.update_checker.UpdateChecker')
    def test_check_version_update_available(self, mock_checker):
        """Test _check_version() when update is available."""
        mock_instance = mock.MagicMock()
        mock_instance.check.return_value = 'New version available'
        mock_checker.return_value = mock_instance

        level, msg = utils._check_version()
        self.assertEqual(level, 1)
        self.assertEqual(msg, 'New version available')
