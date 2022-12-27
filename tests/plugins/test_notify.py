from unittest import mock

from oslo_config import cfg

from aprsd import client, packets
from aprsd import conf  # noqa: F401
from aprsd.plugins import notify as notify_plugin

from .. import fake, test_plugin


CONF = cfg.CONF
DEFAULT_WATCHLIST_CALLSIGNS = fake.FAKE_FROM_CALLSIGN


class TestWatchListPlugin(test_plugin.TestPlugin):
    def setUp(self):
        self.fromcall = fake.FAKE_FROM_CALLSIGN
        self.ack = 1

    def config_and_init(
        self,
        watchlist_enabled=True,
        watchlist_alert_callsign=None,
        watchlist_alert_time_seconds=None,
        watchlist_packet_keep_count=None,
        watchlist_callsigns=DEFAULT_WATCHLIST_CALLSIGNS,
    ):
        CONF.callsign = self.fromcall
        CONF.aprs_network.login = self.fromcall
        CONF.aprs_fi.apiKey = "something"

        # Set the watchlist specific config options
        CONF.watch_list.enabled = watchlist_enabled

        if not watchlist_alert_callsign:
            watchlist_alert_callsign = fake.FAKE_TO_CALLSIGN
        CONF.watch_list.alert_callsign = watchlist_alert_callsign

        if not watchlist_alert_time_seconds:
            watchlist_alert_time_seconds = CONF.watch_list.alert_time_seconds
        CONF.watch_list.alert_time_seconds = watchlist_alert_time_seconds

        if not watchlist_packet_keep_count:
            watchlist_packet_keep_count = CONF.watch_list.packet_keep_count
            CONF.watch_list.packet_keep_count = watchlist_packet_keep_count

        CONF.watch_list.callsigns = watchlist_callsigns


class TestAPRSDWatchListPluginBase(TestWatchListPlugin):

    def test_watchlist_not_enabled(self):
        self.config_and_init(watchlist_enabled=False)
        plugin = fake.FakeWatchListPlugin()

        packet = fake.fake_packet(
            message="version",
            msg_number=1,
        )
        actual = plugin.filter(packet)
        expected = packets.NULL_MESSAGE
        self.assertEqual(expected, actual)

    @mock.patch("aprsd.client.ClientFactory", autospec=True)
    def test_watchlist_not_in_watchlist(self, mock_factory):
        client.factory = mock_factory
        self.config_and_init()
        plugin = fake.FakeWatchListPlugin()

        packet = fake.fake_packet(
            fromcall="FAKE",
            message="version",
            msg_number=1,
        )
        actual = plugin.filter(packet)
        expected = packets.NULL_MESSAGE
        self.assertEqual(expected, actual)


class TestNotifySeenPlugin(TestWatchListPlugin):

    def test_disabled(self):
        self.config_and_init(watchlist_enabled=False)
        plugin = notify_plugin.NotifySeenPlugin()

        packet = fake.fake_packet(
            message="version",
            msg_number=1,
        )
        actual = plugin.filter(packet)
        expected = packets.NULL_MESSAGE
        self.assertEqual(expected, actual)

    @mock.patch("aprsd.client.ClientFactory", autospec=True)
    def test_callsign_not_in_watchlist(self, mock_factory):
        client.factory = mock_factory
        self.config_and_init(watchlist_enabled=False)
        plugin = notify_plugin.NotifySeenPlugin()

        packet = fake.fake_packet(
            message="version",
            msg_number=1,
        )
        actual = plugin.filter(packet)
        expected = packets.NULL_MESSAGE
        self.assertEqual(expected, actual)

    @mock.patch("aprsd.client.ClientFactory", autospec=True)
    @mock.patch("aprsd.packets.WatchList.is_old")
    def test_callsign_in_watchlist_not_old(self, mock_is_old, mock_factory):
        client.factory = mock_factory
        mock_is_old.return_value = False
        self.config_and_init(
            watchlist_enabled=True,
            watchlist_callsigns=["WB4BOR"],
        )
        plugin = notify_plugin.NotifySeenPlugin()

        packet = fake.fake_packet(
            fromcall="WB4BOR",
            message="ping",
            msg_number=1,
        )
        actual = plugin.filter(packet)
        expected = packets.NULL_MESSAGE
        self.assertEqual(expected, actual)

    @mock.patch("aprsd.client.ClientFactory", autospec=True)
    @mock.patch("aprsd.packets.WatchList.is_old")
    def test_callsign_in_watchlist_old_same_alert_callsign(self, mock_is_old, mock_factory):
        client.factory = mock_factory
        mock_is_old.return_value = True
        self.config_and_init(
            watchlist_enabled=True,
            watchlist_alert_callsign="WB4BOR",
            watchlist_callsigns=["WB4BOR"],
        )
        plugin = notify_plugin.NotifySeenPlugin()

        packet = fake.fake_packet(
            fromcall="WB4BOR",
            message="ping",
            msg_number=1,
        )
        actual = plugin.filter(packet)
        expected = packets.NULL_MESSAGE
        self.assertEqual(expected, actual)

    @mock.patch("aprsd.client.ClientFactory", autospec=True)
    @mock.patch("aprsd.packets.WatchList.is_old")
    def test_callsign_in_watchlist_old_send_alert(self, mock_is_old, mock_factory):
        client.factory = mock_factory
        mock_is_old.return_value = True
        notify_callsign = fake.FAKE_TO_CALLSIGN
        fromcall = "WB4BOR"
        self.config_and_init(
            watchlist_enabled=True,
            watchlist_alert_callsign=notify_callsign,
            watchlist_callsigns=["WB4BOR"],
        )
        plugin = notify_plugin.NotifySeenPlugin()

        packet = fake.fake_packet(
            fromcall=fromcall,
            message="ping",
            msg_number=1,
        )
        packet_type = packet.__class__.__name__
        actual = plugin.filter(packet)
        msg = f"{fromcall} was just seen by type:'{packet_type}'"

        self.assertIsInstance(actual, packets.MessagePacket)
        self.assertEqual(fake.FAKE_FROM_CALLSIGN, actual.from_call)
        self.assertEqual(notify_callsign, actual.to_call)
        self.assertEqual(msg, actual.message_text)
