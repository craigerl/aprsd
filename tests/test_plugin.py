import unittest
from unittest import mock

import pytz

import aprsd
from aprsd import config, messaging, packets, stats
from aprsd.fuzzyclock import fuzzy
from aprsd.plugins import fortune as fortune_plugin
from aprsd.plugins import ping as ping_plugin
from aprsd.plugins import query as query_plugin
from aprsd.plugins import time as time_plugin
from aprsd.plugins import version as version_plugin

from . import fake


class TestPlugin(unittest.TestCase):
    def setUp(self):
        self.fromcall = fake.FAKE_FROM_CALLSIGN
        self.ack = 1
        self.config = config.DEFAULT_CONFIG_DICT
        self.config["ham"]["callsign"] = self.fromcall
        self.config["aprs"]["login"] = fake.FAKE_TO_CALLSIGN
        self.config["services"]["aprs.fi"]["apiKey"] = "something"
        # Inintialize the stats object with the config
        stats.APRSDStats(self.config)
        packets.WatchList(config=self.config)
        packets.SeenList(config=self.config)
        messaging.MsgTrack(config=self.config)

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
        fake.FakeBaseThreadsPlugin(self.config)
        mock_create.assert_called_once()

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


class TestFortunePlugin(TestPlugin):
    @mock.patch("shutil.which")
    def test_fortune_fail(self, mock_which):
        mock_which.return_value = None
        fortune = fortune_plugin.FortunePlugin(self.config)
        expected = "FortunePlugin isn't enabled"
        packet = fake.fake_packet(message="fortune")
        actual = fortune.filter(packet)
        self.assertEqual(expected, actual)

    @mock.patch("subprocess.check_output")
    @mock.patch("shutil.which")
    def test_fortune_success(self, mock_which, mock_output):
        mock_which.return_value = "/usr/bin/games/fortune"
        mock_output.return_value = "Funny fortune"
        fortune = fortune_plugin.FortunePlugin(self.config)

        expected = "Funny fortune"
        packet = fake.fake_packet(message="fortune")
        actual = fortune.filter(packet)
        self.assertEqual(expected, actual)


class TestQueryPlugin(TestPlugin):
    @mock.patch("aprsd.messaging.MsgTrack.flush")
    def test_query_flush(self, mock_flush):
        packet = fake.fake_packet(message="!delete")
        query = query_plugin.QueryPlugin(self.config)

        expected = "Deleted ALL pending msgs."
        actual = query.filter(packet)
        mock_flush.assert_called_once()
        self.assertEqual(expected, actual)

    @mock.patch("aprsd.messaging.MsgTrack.restart_delayed")
    def test_query_restart_delayed(self, mock_restart):
        track = messaging.MsgTrack()
        track.data = {}
        packet = fake.fake_packet(message="!4")
        query = query_plugin.QueryPlugin(self.config)

        expected = "No pending msgs to resend"
        actual = query.filter(packet)
        mock_restart.assert_not_called()
        self.assertEqual(expected, actual)
        mock_restart.reset_mock()

        # add a message
        msg = messaging.TextMessage(self.fromcall, "testing", self.ack)
        track.add(msg)
        actual = query.filter(packet)
        mock_restart.assert_called_once()


class TestTimePlugins(TestPlugin):
    @mock.patch("aprsd.plugins.time.TimePlugin._get_local_tz")
    @mock.patch("aprsd.plugins.time.TimePlugin._get_utcnow")
    def test_time(self, mock_utcnow, mock_localtz):
        utcnow = pytz.datetime.datetime.utcnow()
        mock_utcnow.return_value = utcnow
        tz = pytz.timezone("US/Pacific")
        mock_localtz.return_value = tz

        gmt_t = pytz.utc.localize(utcnow)
        local_t = gmt_t.astimezone(tz)

        fake_time = mock.MagicMock()
        h = int(local_t.strftime("%H"))
        m = int(local_t.strftime("%M"))
        fake_time.tm_sec = 13
        time = time_plugin.TimePlugin(self.config)

        packet = fake.fake_packet(
            message="location",
            msg_number=1,
        )

        actual = time.filter(packet)
        self.assertEqual(None, actual)

        cur_time = fuzzy(h, m, 1)

        packet = fake.fake_packet(
            message="time",
            msg_number=1,
        )
        local_short_str = local_t.strftime("%H:%M %Z")
        expected = "{} ({})".format(
            cur_time,
            local_short_str,
        )
        actual = time.filter(packet)
        self.assertEqual(expected, actual)


class TestPingPlugin(TestPlugin):
    @mock.patch("time.localtime")
    def test_ping(self, mock_time):
        fake_time = mock.MagicMock()
        h = fake_time.tm_hour = 16
        m = fake_time.tm_min = 12
        s = fake_time.tm_sec = 55
        mock_time.return_value = fake_time

        ping = ping_plugin.PingPlugin(self.config)

        packet = fake.fake_packet(
            message="location",
            msg_number=1,
        )

        result = ping.filter(packet)
        self.assertEqual(None, result)

        def ping_str(h, m, s):
            return (
                "Pong! "
                + str(h).zfill(2)
                + ":"
                + str(m).zfill(2)
                + ":"
                + str(s).zfill(2)
            )

        packet = fake.fake_packet(
            message="Ping",
            msg_number=1,
        )
        actual = ping.filter(packet)
        expected = ping_str(h, m, s)
        self.assertEqual(expected, actual)

        packet = fake.fake_packet(
            message="ping",
            msg_number=1,
        )
        actual = ping.filter(packet)
        self.assertEqual(expected, actual)


class TestVersionPlugin(TestPlugin):
    @mock.patch("aprsd.plugin.PluginManager.get_plugins")
    def test_version(self, mock_get_plugins):
        expected = f"APRSD ver:{aprsd.__version__} uptime:00:00:00"
        version = version_plugin.VersionPlugin(self.config)

        packet = fake.fake_packet(
            message="No",
            msg_number=1,
        )

        actual = version.filter(packet)
        self.assertEqual(None, actual)

        packet = fake.fake_packet(
            message="version",
            msg_number=1,
        )
        actual = version.filter(packet)
        self.assertEqual(expected, actual)

        packet = fake.fake_packet(
            message="Version",
            msg_number=1,
        )
        actual = version.filter(packet)
        self.assertEqual(expected, actual)
