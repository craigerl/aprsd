from unittest import mock

from oslo_config import cfg

from aprsd import (  # noqa: F401
    client,
    conf,
    packets,
)
from aprsd.client.drivers.registry import DriverRegistry
from aprsd.plugins import notify as notify_plugin

from .. import fake, test_plugin
from ..mock_client_driver import MockClientDriver

CONF = cfg.CONF
DEFAULT_WATCHLIST_CALLSIGNS = fake.FAKE_FROM_CALLSIGN


class TestWatchListPlugin(test_plugin.TestPlugin):
    def setUp(self):
        super().setUp()
        self.fromcall = fake.FAKE_FROM_CALLSIGN
        self.ack = 1

        # Mock APRSISDriver
        self.aprsis_patcher = mock.patch('aprsd.client.drivers.aprsis.APRSISDriver')
        self.mock_aprsis = self.aprsis_patcher.start()
        self.mock_aprsis.is_enabled.return_value = False
        self.mock_aprsis.is_configured.return_value = False

        # Patch the register method to skip Protocol check for MockClientDriver
        # Get the singleton instance and patch it
        registry = DriverRegistry()
        self._original_register = registry.register

        def mock_register(driver):
            # Skip Protocol check for MockClientDriver
            if hasattr(driver, '__name__') and driver.__name__ == 'MockClientDriver':
                registry.drivers.append(driver)
            else:
                self._original_register(driver)

        registry.register = mock_register
        # Store reference to registry for tearDown
        self._patched_registry = registry

        # Register the mock driver
        registry.register(MockClientDriver)

    def tearDown(self):
        super().tearDown()
        if hasattr(self, 'aprsis_patcher'):
            self.aprsis_patcher.stop()
        # Restore original register method if it was patched
        if hasattr(self, '_original_register') and hasattr(self, '_patched_registry'):
            self._patched_registry.register = self._original_register

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
        CONF.aprs_fi.apiKey = 'something'
        # Add mock password
        CONF.aprs_network.password = '12345'

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
            message='version',
            msg_number=1,
        )
        actual = plugin.filter(packet)
        expected = packets.NULL_MESSAGE
        self.assertEqual(expected, actual)

    def test_watchlist_not_in_watchlist(self):
        self.config_and_init()
        plugin = fake.FakeWatchListPlugin()

        packet = fake.fake_packet(
            fromcall='FAKE',
            message='version',
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
            message='version',
            msg_number=1,
        )
        actual = plugin.filter(packet)
        expected = packets.NULL_MESSAGE
        self.assertEqual(expected, actual)

    def test_callsign_not_in_watchlist(self):
        self.config_and_init(watchlist_enabled=False)
        plugin = notify_plugin.NotifySeenPlugin()

        packet = fake.fake_packet(
            message='version',
            msg_number=1,
        )
        actual = plugin.filter(packet)
        expected = packets.NULL_MESSAGE
        self.assertEqual(expected, actual)

    def test_callsign_in_watchlist_not_old(self):
        self.config_and_init(
            watchlist_enabled=True,
            watchlist_callsigns=['WB4BOR'],
        )
        plugin = notify_plugin.NotifySeenPlugin()

        packet = fake.fake_packet(
            fromcall='WB4BOR',
            message='ping',
            msg_number=1,
        )
        # Simulate WatchList.rx() being called first (with recent timestamp)
        # This will set was_old_before_update to False since it's not old
        packets.WatchList().rx(packet)
        actual = plugin.filter(packet)
        expected = packets.NULL_MESSAGE
        self.assertEqual(expected, actual)

    def test_callsign_in_watchlist_old_same_alert_callsign(self):
        import datetime

        self.config_and_init(
            watchlist_enabled=True,
            watchlist_alert_callsign='WB4BOR',
            watchlist_callsigns=['WB4BOR'],
            watchlist_alert_time_seconds=60,
        )
        plugin = notify_plugin.NotifySeenPlugin()

        # Set up WatchList with an old timestamp
        wl = packets.WatchList()
        old_time = datetime.datetime.now() - datetime.timedelta(seconds=120)
        with wl.lock:
            wl.data['WB4BOR'] = {
                'last': old_time,
                'packet': None,
                'was_old_before_update': False,
            }

        packet = fake.fake_packet(
            fromcall='WB4BOR',
            message='ping',
            msg_number=1,
        )
        # Simulate WatchList.rx() being called first
        # This will set was_old_before_update to True since it was old
        wl.rx(packet)
        actual = plugin.filter(packet)
        expected = packets.NULL_MESSAGE
        self.assertEqual(expected, actual)

    def test_callsign_in_watchlist_old_send_alert(self):
        import datetime

        notify_callsign = fake.FAKE_TO_CALLSIGN
        fromcall = 'WB4BOR'
        self.config_and_init(
            watchlist_enabled=True,
            watchlist_alert_callsign=notify_callsign,
            watchlist_callsigns=['WB4BOR'],
            watchlist_alert_time_seconds=60,
        )
        plugin = notify_plugin.NotifySeenPlugin()

        # Set up WatchList with an old timestamp
        wl = packets.WatchList()
        old_time = datetime.datetime.now() - datetime.timedelta(seconds=120)
        with wl.lock:
            wl.data[fromcall] = {
                'last': old_time,
                'packet': None,
                'was_old_before_update': False,
            }

        packet = fake.fake_packet(
            fromcall=fromcall,
            message='ping',
            msg_number=1,
        )
        # Simulate WatchList.rx() being called first
        # This will set was_old_before_update to True since it was old
        wl.rx(packet)
        packet_type = packet.__class__.__name__
        actual = plugin.filter(packet)
        msg = f"{fromcall} was just seen by type:'{packet_type}'"

        self.assertIsInstance(actual, packets.MessagePacket)
        self.assertEqual(fake.FAKE_FROM_CALLSIGN, actual.from_call)
        self.assertEqual(notify_callsign, actual.to_call)
        self.assertEqual(msg, actual.message_text)
        # Verify that mark_as_new was called to prevent duplicate notifications
        # by checking that was_old_before_update is now False
        self.assertFalse(wl.was_old_before_last_update(fromcall))
