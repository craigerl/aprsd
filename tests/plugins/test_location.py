from unittest import mock

from aprsd.plugins import location as location_plugin

from .. import fake, test_plugin


class TestLocationPlugin(test_plugin.TestPlugin):

    @mock.patch("aprsd.config.Config.check_option")
    def test_location_not_enabled_missing_aprs_fi_key(self, mock_check):
        # When the aprs.fi api key isn't set, then
        # the LocationPlugin will be disabled.
        mock_check.side_effect = Exception
        fortune = location_plugin.LocationPlugin(self.config)
        expected = "LocationPlugin isn't enabled"
        packet = fake.fake_packet(message="location")
        actual = fortune.filter(packet)
        self.assertEqual(expected, actual)

    @mock.patch("aprsd.plugin_utils.get_aprs_fi")
    def test_location_failed_aprs_fi_location(self, mock_check):
        # When the aprs.fi api key isn't set, then
        # the LocationPlugin will be disabled.
        mock_check.side_effect = Exception
        fortune = location_plugin.LocationPlugin(self.config)
        expected = "Failed to fetch aprs.fi location"
        packet = fake.fake_packet(message="location")
        actual = fortune.filter(packet)
        self.assertEqual(expected, actual)

    @mock.patch("aprsd.plugin_utils.get_aprs_fi")
    def test_location_failed_aprs_fi_location_no_entries(self, mock_check):
        # When the aprs.fi api key isn't set, then
        # the LocationPlugin will be disabled.
        mock_check.return_value = {"entries": []}
        fortune = location_plugin.LocationPlugin(self.config)
        expected = "Failed to fetch aprs.fi location"
        packet = fake.fake_packet(message="location")
        actual = fortune.filter(packet)
        self.assertEqual(expected, actual)

    @mock.patch("aprsd.plugin_utils.get_aprs_fi")
    @mock.patch("aprsd.plugin_utils.get_weather_gov_for_gps")
    @mock.patch("time.time")
    def test_location_unknown_gps(self, mock_time, mock_weather, mock_check_aprs):
        # When the aprs.fi api key isn't set, then
        # the LocationPlugin will be disabled.
        mock_check_aprs.return_value = {
            "entries": [
                {
                    "lat": 10,
                    "lng": 11,
                    "lasttime": 10,
                },
            ],
        }
        mock_weather.side_effect = Exception
        mock_time.return_value = 10
        fortune = location_plugin.LocationPlugin(self.config)
        expected = "KFAKE: Unknown Location 0' 10,11 0.0h ago"
        packet = fake.fake_packet(message="location")
        actual = fortune.filter(packet)
        self.assertEqual(expected, actual)

    @mock.patch("aprsd.plugin_utils.get_aprs_fi")
    @mock.patch("aprsd.plugin_utils.get_weather_gov_for_gps")
    @mock.patch("time.time")
    def test_location_works(self, mock_time, mock_weather, mock_check_aprs):
        # When the aprs.fi api key isn't set, then
        # the LocationPlugin will be disabled.
        mock_check_aprs.return_value = {
            "entries": [
                {
                    "lat": 10,
                    "lng": 11,
                    "lasttime": 10,
                },
            ],
        }
        expected_town = "Appomattox, VA"
        wx_data = {"location": {"areaDescription": expected_town}}
        mock_weather.return_value = wx_data
        mock_time.return_value = 10
        fortune = location_plugin.LocationPlugin(self.config)
        expected = f"KFAKE: {expected_town} 0' 10,11 0.0h ago"
        packet = fake.fake_packet(message="location")
        actual = fortune.filter(packet)
        self.assertEqual(expected, actual)
