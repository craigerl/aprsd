from unittest import mock

from oslo_config import cfg

from aprsd import conf  # noqa: F401
from aprsd.plugins import ping as ping_plugin

from .. import fake, test_plugin


CONF = cfg.CONF


class TestPingPlugin(test_plugin.TestPlugin):
    @mock.patch("time.localtime")
    def test_ping(self, mock_time):
        fake_time = mock.MagicMock()
        h = fake_time.tm_hour = 16
        m = fake_time.tm_min = 12
        s = fake_time.tm_sec = 55
        mock_time.return_value = fake_time

        CONF.callsign = fake.FAKE_TO_CALLSIGN
        ping = ping_plugin.PingPlugin()

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
