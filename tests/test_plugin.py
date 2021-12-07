import unittest
from unittest import mock

from aprsd import config as aprsd_config
from aprsd import messaging, packets, stats

from . import fake


class TestPlugin(unittest.TestCase):

    def setUp(self) -> None:
        self.fromcall = fake.FAKE_FROM_CALLSIGN
        self.ack = 1
        self.config_and_init()

    def tearDown(self) -> None:
        stats.APRSDStats._instance = None
        packets.WatchList._instance = None
        packets.SeenList._instance = None
        messaging.MsgTrack._instance = None
        self.config = None

    def config_and_init(self, config=None):
        if not config:
            self.config = aprsd_config.Config(aprsd_config.DEFAULT_CONFIG_DICT)
            self.config["ham"]["callsign"] = self.fromcall
            self.config["aprs"]["login"] = fake.FAKE_TO_CALLSIGN
            self.config["services"]["aprs.fi"]["apiKey"] = "something"
        else:
            self.config = config

        # Inintialize the stats object with the config
        stats.APRSDStats(self.config)
        packets.WatchList(config=self.config)
        packets.SeenList(config=self.config)
        messaging.MsgTrack(config=self.config)


class TestPluginBase(TestPlugin):

    @mock.patch.object(fake.FakeBaseNoThreadsPlugin, "process")
    def test_base_plugin_no_threads(self, mock_process):
        p = fake.FakeBaseNoThreadsPlugin(self.config)

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
        p = fake.FakeBaseThreadsPlugin(self.config)
        mock_create.assert_called_once()
        p.stop_threads()

    def test_base_plugin_threads(self):
        p = fake.FakeBaseThreadsPlugin(self.config)
        actual = p.create_threads()
        self.assertTrue(isinstance(actual, fake.FakeThread))
        p.stop_threads()

    @mock.patch.object(fake.FakeRegexCommandPlugin, "process")
    def test_regex_base_not_called(self, mock_process):
        p = fake.FakeRegexCommandPlugin(self.config)
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
            message="F",
            message_format=packets.PACKET_TYPE_MICE,
        )
        expected = None
        actual = p.filter(packet)
        self.assertEqual(expected, actual)
        mock_process.assert_not_called()

        packet = fake.fake_packet(
            message="f",
            message_format=packets.PACKET_TYPE_ACK,
        )
        expected = None
        actual = p.filter(packet)
        self.assertEqual(expected, actual)
        mock_process.assert_not_called()

    @mock.patch.object(fake.FakeRegexCommandPlugin, "process")
    def test_regex_base_assert_called(self, mock_process):
        p = fake.FakeRegexCommandPlugin(self.config)
        packet = fake.fake_packet(message="f")
        p.filter(packet)
        mock_process.assert_called_once()

    def test_regex_base_process_called(self):
        p = fake.FakeRegexCommandPlugin(self.config)

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
