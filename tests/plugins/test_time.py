from unittest import mock

from oslo_config import cfg
import pytz

from aprsd.plugins import time as time_plugin
from aprsd.utils import fuzzy

from .. import fake, test_plugin


CONF = cfg.CONF


class TestTimePlugins(test_plugin.TestPlugin):

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
        CONF.callsign = fake.FAKE_TO_CALLSIGN
        time = time_plugin.TimePlugin()

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
