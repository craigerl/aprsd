import unittest
from unittest import mock

from oslo_config import cfg

from aprsd import conf  # noqa: F401
from aprsd import packets
from aprsd import plugin as aprsd_plugin
from aprsd import plugins, stats
from aprsd.packets import core

from . import fake


CONF = cfg.CONF


class TestPluginManager(unittest.TestCase):

    def setUp(self) -> None:
        self.fromcall = fake.FAKE_FROM_CALLSIGN
        self.config_and_init()

    def tearDown(self) -> None:
        self.config = None
        aprsd_plugin.PluginManager._instance = None

    def config_and_init(self):
        CONF.callsign = self.fromcall
        CONF.aprs_network.login = fake.FAKE_TO_CALLSIGN
        CONF.aprs_fi.apiKey = "something"
        CONF.enabled_plugins = "aprsd.plugins.ping.PingPlugin"
        CONF.enable_save = False

    def test_get_plugins_no_plugins(self):
        CONF.enabled_plugins = []
        pm = aprsd_plugin.PluginManager()
        plugin_list = pm.get_plugins()
        self.assertEqual([], plugin_list)

    def test_get_plugins_with_plugins(self):
        CONF.enabled_plugins = ["aprsd.plugins.ping.PingPlugin"]
        pm = aprsd_plugin.PluginManager()
        plugin_list = pm.get_plugins()
        self.assertEqual([], plugin_list)
        pm.setup_plugins()
        plugin_list = pm.get_plugins()
        print(plugin_list)
        self.assertIsInstance(plugin_list, list)
        self.assertIsInstance(
            plugin_list[0],
            (
                aprsd_plugin.HelpPlugin,
                plugins.ping.PingPlugin,
            ),
        )

    def test_get_watchlist_plugins(self):
        pm = aprsd_plugin.PluginManager()
        plugin_list = pm.get_plugins()
        self.assertEqual([], plugin_list)
        pm.setup_plugins()
        plugin_list = pm.get_watchlist_plugins()
        self.assertIsInstance(plugin_list, list)
        self.assertEqual(0, len(plugin_list))

    def test_get_message_plugins(self):
        CONF.enabled_plugins = ["aprsd.plugins.ping.PingPlugin"]
        pm = aprsd_plugin.PluginManager()
        plugin_list = pm.get_plugins()
        self.assertEqual([], plugin_list)
        pm.setup_plugins()
        plugin_list = pm.get_message_plugins()
        self.assertIsInstance(plugin_list, list)
        self.assertEqual(2, len(plugin_list))
        self.assertIsInstance(
            plugin_list[0],
            (
                aprsd_plugin.HelpPlugin,
                plugins.ping.PingPlugin,
            ),
        )


class TestPlugin(unittest.TestCase):

    def setUp(self) -> None:
        self.fromcall = fake.FAKE_FROM_CALLSIGN
        self.ack = 1
        self.config_and_init()

    def tearDown(self) -> None:
        stats.APRSDStats._instance = None
        packets.WatchList._instance = None
        packets.SeenList._instance = None
        packets.PacketTrack._instance = None
        self.config = None

    def config_and_init(self):
        CONF.callsign = self.fromcall
        CONF.aprs_network.login = fake.FAKE_TO_CALLSIGN
        CONF.aprs_fi.apiKey = "something"
        CONF.enabled_plugins = "aprsd.plugins.ping.PingPlugin"
        CONF.enable_save = False


class TestPluginBase(TestPlugin):

    @mock.patch.object(fake.FakeBaseNoThreadsPlugin, "process")
    def test_base_plugin_no_threads(self, mock_process):
        p = fake.FakeBaseNoThreadsPlugin()

        expected = []
        actual = p.create_threads()
        self.assertEqual(expected, actual)

        expected = "1.0"
        actual = p.version
        self.assertEqual(expected, actual)

        expected = 0
        actual = p.message_counter
        self.assertEqual(expected, actual)

        expected = None
        actual = p.filter(fake.fake_packet())
        self.assertEqual(expected, actual)
        mock_process.assert_not_called()

    @mock.patch.object(fake.FakeBaseThreadsPlugin, "create_threads")
    def test_base_plugin_threads_created(self, mock_create):
        p = fake.FakeBaseThreadsPlugin()
        mock_create.assert_called_once()
        p.stop_threads()

    def test_base_plugin_threads(self):
        p = fake.FakeBaseThreadsPlugin()
        actual = p.create_threads()
        self.assertTrue(isinstance(actual, fake.FakeThread))
        p.stop_threads()

    @mock.patch.object(fake.FakeRegexCommandPlugin, "process")
    def test_regex_base_not_called(self, mock_process):
        CONF.callsign = fake.FAKE_TO_CALLSIGN
        p = fake.FakeRegexCommandPlugin()
        packet = fake.fake_packet(message="a")
        expected = None
        actual = p.filter(packet)
        self.assertEqual(expected, actual)
        mock_process.assert_not_called()

        packet = fake.fake_packet(tocall="notMe", message="f")
        expected = None
        actual = p.filter(packet)
        self.assertEqual(expected, actual)
        mock_process.assert_not_called()

        packet = fake.fake_packet(
            message_format=core.PACKET_TYPE_MICE,
        )
        expected = packets.NULL_MESSAGE
        actual = p.filter(packet)
        self.assertEqual(expected, actual)
        mock_process.assert_not_called()

        packet = fake.fake_packet(
            message_format=core.PACKET_TYPE_ACK,
        )
        expected = packets.NULL_MESSAGE
        actual = p.filter(packet)
        self.assertEqual(expected, actual)
        mock_process.assert_not_called()

    @mock.patch.object(fake.FakeRegexCommandPlugin, "process")
    def test_regex_base_assert_called(self, mock_process):
        CONF.callsign = fake.FAKE_TO_CALLSIGN
        p = fake.FakeRegexCommandPlugin()
        packet = fake.fake_packet(message="f")
        p.filter(packet)
        mock_process.assert_called_once()

    def test_regex_base_process_called(self):
        CONF.callsign = fake.FAKE_TO_CALLSIGN
        p = fake.FakeRegexCommandPlugin()

        packet = fake.fake_packet(message="f")
        expected = fake.FAKE_MESSAGE_TEXT
        actual = p.filter(packet)
        self.assertEqual(expected, actual)

        packet = fake.fake_packet(message="F")
        expected = fake.FAKE_MESSAGE_TEXT
        actual = p.filter(packet)
        self.assertEqual(expected, actual)

        packet = fake.fake_packet(message="fake")
        expected = fake.FAKE_MESSAGE_TEXT
        actual = p.filter(packet)
        self.assertEqual(expected, actual)

        packet = fake.fake_packet(message="FAKE")
        expected = fake.FAKE_MESSAGE_TEXT
        actual = p.filter(packet)
        self.assertEqual(expected, actual)
