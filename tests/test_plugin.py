# -*- coding: utf-8 -*-
import sys
import unittest
from unittest import mock

import pytest

import aprsd
from aprsd import plugin
from aprsd.fuzzyclock import fuzzy


class testPlugin(unittest.TestCase):
    def setUp(self):
        self.config = mock.MagicMock()

    @mock.patch("time.localtime")
    def test_Time(self, mock_time):
        fake_time = mock.MagicMock()
        h = fake_time.tm_hour = 16
        m = fake_time.tm_min = 12
        s = fake_time.tm_sec = 55
        mock_time.return_value = fake_time
        time_plugin = plugin.TimePlugin(self.config)

        fromcall = "KFART"
        message = "location"
        ack = 1

        actual = time_plugin.run(fromcall, message, ack)
        self.assertEqual(None, actual)

        cur_time = fuzzy(h, m, 1)

        message = "time"
        expected = "{} ({}:{} PDT) ({})".format(
            cur_time, str(h), str(m).rjust(2, "0"), message.rstrip()
        )
        actual = time_plugin.run(fromcall, message, ack)
        self.assertEqual(expected, actual)

    @mock.patch("time.localtime")
    def test_Ping(self, mock_time):
        fake_time = mock.MagicMock()
        h = fake_time.tm_hour = 16
        m = fake_time.tm_min = 12
        s = fake_time.tm_sec = 55
        mock_time.return_value = fake_time

        ping = plugin.PingPlugin(self.config)

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
        version_plugin = plugin.VersionPlugin(self.config)

        fromcall = "KFART"
        message = "No"
        ack = 1

        actual = version_plugin.run(fromcall, message, ack)
        self.assertEqual(None, actual)

        message = "version"
        actual = version_plugin.run(fromcall, message, ack)
        self.assertEqual(expected, actual)

        message = "Version"
        actual = version_plugin.run(fromcall, message, ack)
        self.assertEqual(expected, actual)
