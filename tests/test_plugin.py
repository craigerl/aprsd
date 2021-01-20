import unittest
from unittest import mock

import aprsd
from aprsd import messaging
from aprsd.fuzzyclock import fuzzy
from aprsd.plugins import fortune as fortune_plugin
from aprsd.plugins import ping as ping_plugin
from aprsd.plugins import query as query_plugin
from aprsd.plugins import time as time_plugin
from aprsd.plugins import version as version_plugin
import pytz


class TestPlugin(unittest.TestCase):
    def setUp(self):
        self.fromcall = "KFART"
        self.ack = 1
        self.config = {"ham": {"callsign": self.fromcall}}

    @mock.patch("shutil.which")
    def test_fortune_fail(self, mock_which):
        fortune = fortune_plugin.FortunePlugin(self.config)
        mock_which.return_value = None
        message = "fortune"
        expected = "Fortune command not installed"
        actual = fortune.run(self.fromcall, message, self.ack)
        self.assertEqual(expected, actual)

    @mock.patch("subprocess.check_output")
    @mock.patch("shutil.which")
    def test_fortune_success(self, mock_which, mock_output):
        fortune = fortune_plugin.FortunePlugin(self.config)
        mock_which.return_value = "/usr/bin/games"

        mock_output.return_value = "Funny fortune"

        message = "fortune"
        expected = "Funny fortune"
        actual = fortune.run(self.fromcall, message, self.ack)
        self.assertEqual(expected, actual)

    @mock.patch("aprsd.messaging.MsgTrack.flush")
    def test_query_flush(self, mock_flush):
        message = "!delete"
        query = query_plugin.QueryPlugin(self.config)

        expected = "Deleted ALL pending msgs."
        actual = query.run(self.fromcall, message, self.ack)
        mock_flush.assert_called_once()
        self.assertEqual(expected, actual)

    @mock.patch("aprsd.messaging.MsgTrack.restart_delayed")
    def test_query_restart_delayed(self, mock_restart):
        track = messaging.MsgTrack()
        track.track = {}
        message = "!4"
        query = query_plugin.QueryPlugin(self.config)

        expected = "No pending msgs to resend"
        actual = query.run(self.fromcall, message, self.ack)
        mock_restart.assert_not_called()
        self.assertEqual(expected, actual)
        mock_restart.reset_mock()

        # add a message
        msg = messaging.TextMessage(self.fromcall, "testing", self.ack)
        track.add(msg)
        actual = query.run(self.fromcall, message, self.ack)
        mock_restart.assert_called_once()

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

        fromcall = "KFART"
        message = "location"
        ack = 1

        actual = time.run(fromcall, message, ack)
        self.assertEqual(None, actual)

        cur_time = fuzzy(h, m, 1)

        message = "time"
        local_short_str = local_t.strftime("%H:%M %Z")
        expected = "{} ({})".format(
            cur_time,
            local_short_str,
        )
        actual = time.run(fromcall, message, ack)
        self.assertEqual(expected, actual)

    @mock.patch("time.localtime")
    def test_ping(self, mock_time):
        fake_time = mock.MagicMock()
        h = fake_time.tm_hour = 16
        m = fake_time.tm_min = 12
        s = fake_time.tm_sec = 55
        mock_time.return_value = fake_time

        ping = ping_plugin.PingPlugin(self.config)

        fromcall = "KFART"
        message = "location"
        ack = 1

        result = ping.run(fromcall, message, ack)
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

        message = "Ping"
        actual = ping.run(fromcall, message, ack)
        expected = ping_str(h, m, s)
        self.assertEqual(expected, actual)

        message = "ping"
        actual = ping.run(fromcall, message, ack)
        self.assertEqual(expected, actual)

    def test_version(self):
        expected = "APRSD version '{}'".format(aprsd.__version__)
        version = version_plugin.VersionPlugin(self.config)

        fromcall = "KFART"
        message = "No"
        ack = 1

        actual = version.run(fromcall, message, ack)
        self.assertEqual(None, actual)

        message = "version"
        actual = version.run(fromcall, message, ack)
        self.assertEqual(expected, actual)

        message = "Version"
        actual = version.run(fromcall, message, ack)
        self.assertEqual(expected, actual)
