from unittest import mock

from oslo_config import cfg

from aprsd import conf  # noqa: F401
from aprsd.plugins import location as location_plugin

from .. import fake, test_plugin


CONF = cfg.CONF


class TestLocationPlugin(test_plugin.TestPlugin):

    def test_location_not_enabled_missing_aprs_fi_key(self):
        # When the aprs.fi api key isn't set, then
        # the LocationPlugin will be disabled.
        CONF.callsign = fake.FAKE_TO_CALLSIGN
        CONF.aprs_fi.apiKey = None
        fortune = location_plugin.LocationPlugin()
        expected = "LocationPlugin isn't enabled"
        packet = fake.fake_packet(message="location")
        actual = fortune.filter(packet)
        self.assertEqual(expected, actual)

    @mock.patch("aprsd.plugin_utils.get_aprs_fi")
    def test_location_failed_aprs_fi_location(self, mock_check):
        # When the aprs.fi api key isn't set, then
        # the LocationPlugin will be disabled.
        mock_check.side_effect = Exception
        CONF.callsign = fake.FAKE_TO_CALLSIGN
        fortune = location_plugin.LocationPlugin()
        expected = "Failed to fetch aprs.fi location"
        packet = fake.fake_packet(message="location")
        actual = fortune.filter(packet)
        self.assertEqual(expected, actual)

    @mock.patch("aprsd.plugin_utils.get_aprs_fi")
    def test_location_failed_aprs_fi_location_no_entries(self, mock_check):
        # When the aprs.fi api key isn't set, then
        # the LocationPlugin will be disabled.
        mock_check.return_value = {"entries": []}
        CONF.callsign = fake.FAKE_TO_CALLSIGN
        fortune = location_plugin.LocationPlugin()
        expected = "Failed to fetch aprs.fi location"
        packet = fake.fake_packet(message="location")
        actual = fortune.filter(packet)
        self.assertEqual(expected, actual)

    @mock.patch("aprsd.plugin_utils.get_aprs_fi")
    @mock.patch("geopy.geocoders.Nominatim.reverse")
    @mock.patch("time.time")
    def test_location_unknown_gps(self, mock_time, mock_geocode, mock_check_aprs):
        # When the aprs.fi api key isn't set, then
        # the LocationPlugin will be disabled.
        mock_check_aprs.return_value = {
            "entries": [
                {
                    "lat": 1,
                    "lng": 1,
                    "lasttime": 10,
                },
            ],
        }
        mock_geocode.side_effect = Exception
        mock_time.return_value = 10
        CONF.callsign = fake.FAKE_TO_CALLSIGN
        fortune = location_plugin.LocationPlugin()
        expected = "KFAKE: Unknown Location 0' 1.00,1.00 0.0h ago"
        packet = fake.fake_packet(message="location")
        actual = fortune.filter(packet)
        self.assertEqual(expected, actual)

    @mock.patch("aprsd.plugin_utils.get_aprs_fi")
    @mock.patch("geopy.geocoders.Nominatim.reverse")
    @mock.patch("time.time")
    def test_location_works(self, mock_time, mock_geocode, mock_check_aprs):
        # When the aprs.fi api key isn't set, then
        # the LocationPlugin will be disabled.
        mock_check_aprs.return_value = {
            "entries": [
                {
                    "lat": 1,
                    "lng": 1,
                    "lasttime": 10,
                },
            ],
        }
        expected = "Appomattox"
        state = "VA"

        class TempLocation:
            raw = {
                "address": {
                    "county": expected,
                    "country_code": "us",
                    "state": state,
                    "country": "United States",
                },
            }
        mock_geocode.return_value = TempLocation()
        mock_time.return_value = 10
        CONF.callsign = fake.FAKE_TO_CALLSIGN
        fortune = location_plugin.LocationPlugin()
        expected = f"KFAKE: {expected}, {state} 0' 1.00,1.00 0.0h ago"
        packet = fake.fake_packet(message="location")
        actual = fortune.filter(packet)
        self.assertEqual(expected, actual)
