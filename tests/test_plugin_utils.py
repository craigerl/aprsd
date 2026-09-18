import unittest
from unittest import mock

from aprsd import plugin_utils


class TestPluginUtilsTimeouts(unittest.TestCase):
    """Every outbound requests.get() must use an explicit timeout."""

    def _assert_timeout(self, mock_get):
        args, kwargs = mock_get.call_args
        self.assertEqual(kwargs.get('timeout'), 10)

    def test_get_aprs_fi_uses_timeout(self):
        with (
            mock.patch('aprsd.plugin_utils.requests.get') as mock_get,
            mock.patch('aprsd.plugin_utils.json.loads') as mock_loads,
        ):
            mock_loads.return_value = {}
            plugin_utils.get_aprs_fi('key', 'N0CALL')
            self._assert_timeout(mock_get)

    def test_get_weather_gov_for_gps_uses_timeout(self):
        with (
            mock.patch('aprsd.plugin_utils.requests.get') as mock_get,
            mock.patch('aprsd.plugin_utils.json.loads') as mock_loads,
        ):
            mock_loads.return_value = {}
            plugin_utils.get_weather_gov_for_gps(37.7, -122.4)
            self._assert_timeout(mock_get)

    def test_get_weather_gov_metar_uses_timeout(self):
        with (
            mock.patch('aprsd.plugin_utils.requests.get') as mock_get,
            mock.patch('aprsd.plugin_utils.json.loads') as mock_loads,
        ):
            mock_loads.return_value = {}
            plugin_utils.get_weather_gov_metar('KJFK')
            self._assert_timeout(mock_get)

    def test_fetch_openweathermap_uses_timeout(self):
        with (
            mock.patch('aprsd.plugin_utils.requests.get') as mock_get,
            mock.patch('aprsd.plugin_utils.json.loads') as mock_loads,
        ):
            mock_loads.return_value = {}
            plugin_utils.fetch_openweathermap('key', 37.7, -122.4)
            self._assert_timeout(mock_get)
