from unittest import mock

from aprsd import client
from aprsd import config as aprsd_config
from aprsd import messaging, packets
from aprsd.plugins import notify as notify_plugin

from .. import fake, test_plugin


DEFAULT_WATCHLIST_CALLSIGNS = [fake.FAKE_FROM_CALLSIGN]


class TestWatchListPlugin(test_plugin.TestPlugin):
    def setUp(self):
        self.fromcall = fake.FAKE_FROM_CALLSIGN
        self.ack = 1

    def _config(
        self,
        watchlist_enabled=True,
        watchlist_alert_callsign=None,
        watchlist_alert_time_seconds=None,
        watchlist_packet_keep_count=None,
        watchlist_callsigns=DEFAULT_WATCHLIST_CALLSIGNS,
    ):
        _config = aprsd_config.Config(aprsd_config.DEFAULT_CONFIG_DICT)
        default_wl = aprsd_config.DEFAULT_CONFIG_DICT["aprsd"]["watch_list"]

        _config["ham"]["callsign"] = self.fromcall
        _config["aprs"]["login"] = fake.FAKE_TO_CALLSIGN
        _config["services"]["aprs.fi"]["apiKey"] = "something"

        # Set the watchlist specific config options

        _config["aprsd"]["watch_list"]["enabled"] = watchlist_enabled
        if not watchlist_alert_callsign:
            watchlist_alert_callsign = fake.FAKE_TO_CALLSIGN
        _config["aprsd"]["watch_list"]["alert_callsign"] = watchlist_alert_callsign

        if not watchlist_alert_time_seconds:
            watchlist_alert_time_seconds = default_wl["alert_time_seconds"]
        _config["aprsd"]["watch_list"]["alert_time_seconds"] = watchlist_alert_time_seconds

        if not watchlist_packet_keep_count:
            watchlist_packet_keep_count = default_wl["packet_keep_count"]
        _config["aprsd"]["watch_list"]["packet_keep_count"] = watchlist_packet_keep_count

        _config["aprsd"]["watch_list"]["callsigns"] = watchlist_callsigns
        return _config


class TestAPRSDWatchListPluginBase(TestWatchListPlugin):

    def test_watchlist_not_enabled(self):
        config = self._config(watchlist_enabled=False)
        self.config_and_init(config=config)
        plugin = fake.FakeWatchListPlugin(self.config)

        packet = fake.fake_packet(
            message="version",
            msg_number=1,
        )
        actual = plugin.filter(packet)
        expected = messaging.NULL_MESSAGE
        self.assertEqual(expected, actual)

    @mock.patch("aprsd.client.ClientFactory", autospec=True)
    def test_watchlist_not_in_watchlist(self, mock_factory):
        client.factory = mock_factory
        config = self._config()
        self.config_and_init(config=config)
        plugin = fake.FakeWatchListPlugin(self.config)

        packet = fake.fake_packet(
            fromcall="FAKE",
            message="version",
            msg_number=1,
        )
        actual = plugin.filter(packet)
        expected = messaging.NULL_MESSAGE
        self.assertEqual(expected, actual)


class TestNotifySeenPlugin(TestWatchListPlugin):

    def test_disabled(self):
        config = self._config(watchlist_enabled=False)
        self.config_and_init(config=config)
        plugin = notify_plugin.NotifySeenPlugin(self.config)

        packet = fake.fake_packet(
            message="version",
            msg_number=1,
        )
        actual = plugin.filter(packet)
        expected = messaging.NULL_MESSAGE
        self.assertEqual(expected, actual)

    @mock.patch("aprsd.client.ClientFactory", autospec=True)
    def test_callsign_not_in_watchlist(self, mock_factory):
        client.factory = mock_factory
        config = self._config(watchlist_enabled=False)
        self.config_and_init(config=config)
        plugin = notify_plugin.NotifySeenPlugin(self.config)

        packet = fake.fake_packet(
            message="version",
            msg_number=1,
        )
        actual = plugin.filter(packet)
        expected = messaging.NULL_MESSAGE
        self.assertEqual(expected, actual)

    @mock.patch("aprsd.client.ClientFactory", autospec=True)
    @mock.patch("aprsd.packets.WatchList.is_old")
    def test_callsign_in_watchlist_not_old(self, mock_is_old, mock_factory):
        client.factory = mock_factory
        mock_is_old.return_value = False
        config = self._config(
            watchlist_enabled=True,
            watchlist_callsigns=["WB4BOR"],
        )
        self.config_and_init(config=config)
        plugin = notify_plugin.NotifySeenPlugin(self.config)

        packet = fake.fake_packet(
            fromcall="WB4BOR",
            message="ping",
            msg_number=1,
        )
        actual = plugin.filter(packet)
        expected = messaging.NULL_MESSAGE
        self.assertEqual(expected, actual)

    @mock.patch("aprsd.client.ClientFactory", autospec=True)
    @mock.patch("aprsd.packets.WatchList.is_old")
    def test_callsign_in_watchlist_old_same_alert_callsign(self, mock_is_old, mock_factory):
        client.factory = mock_factory
        mock_is_old.return_value = True
        config = self._config(
            watchlist_enabled=True,
            watchlist_alert_callsign="WB4BOR",
            watchlist_callsigns=["WB4BOR"],
        )
        self.config_and_init(config=config)
        plugin = notify_plugin.NotifySeenPlugin(self.config)

        packet = fake.fake_packet(
            fromcall="WB4BOR",
            message="ping",
            msg_number=1,
        )
        actual = plugin.filter(packet)
        expected = messaging.NULL_MESSAGE
        self.assertEqual(expected, actual)

    @mock.patch("aprsd.client.ClientFactory", autospec=True)
    @mock.patch("aprsd.packets.WatchList.is_old")
    def test_callsign_in_watchlist_old_send_alert(self, mock_is_old, mock_factory):
        client.factory = mock_factory
        mock_is_old.return_value = True
        notify_callsign = "KFAKE"
        fromcall = "WB4BOR"
        config = self._config(
            watchlist_enabled=True,
            watchlist_alert_callsign=notify_callsign,
            watchlist_callsigns=["WB4BOR"],
        )
        self.config_and_init(config=config)
        plugin = notify_plugin.NotifySeenPlugin(self.config)

        packet = fake.fake_packet(
            fromcall=fromcall,
            message="ping",
            msg_number=1,
        )
        packet_type = packets.get_packet_type(packet)
        actual = plugin.filter(packet)
        msg = f"{fromcall} was just seen by type:'{packet_type}'"

        self.assertIsInstance(actual, messaging.TextMessage)
        self.assertEqual(fake.FAKE_TO_CALLSIGN, actual.fromcall)
        self.assertEqual(notify_callsign, actual.tocall)
        self.assertEqual(msg, actual.message)
