import unittest
from unittest import mock

from aprsd import plugin_utils


class TestPluginUtilsTimeouts(unittest.TestCase):
    """Every outbound requests.get() must use an explicit timeout."""

    def test_request_timeout_is_positive(self):
        self.assertIsInstance(plugin_utils.REQUEST_TIMEOUT, int)
        self.assertGreater(plugin_utils.REQUEST_TIMEOUT, 0)

    def _assert_timeout(self, mock_get):
        args, kwargs = mock_get.call_args
        self.assertEqual(kwargs.get('timeout'), plugin_utils.REQUEST_TIMEOUT)

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

    def test_get_weather_gov_metar_returns_parsed_json(self):
        """get_weather_gov_metar must return the parsed JSON dict.

        It previously called json.loads(response) with a requests.Response
        object, which raises TypeError: the JSON object must be str, bytes
        or bytearray.  That made every METAR-by-station request fail.
        """

        class Response:
            text = '{"properties": {"rawMessage": "BOGUSMETAR"}}'

            def raise_for_status(self):
                pass

        with mock.patch('aprsd.plugin_utils.requests.get') as mock_get:
            mock_get.return_value = Response()
            result = plugin_utils.get_weather_gov_metar('KJFK')

        self.assertEqual(result, {'properties': {'rawMessage': 'BOGUSMETAR'}})

    def test_fetch_openweathermap_uses_timeout(self):
        with (
            mock.patch('aprsd.plugin_utils.requests.get') as mock_get,
            mock.patch('aprsd.plugin_utils.json.loads') as mock_loads,
        ):
            mock_loads.return_value = {}
            plugin_utils.fetch_openweathermap('key', 37.7, -122.4)
            self._assert_timeout(mock_get)
