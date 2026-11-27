import tempfile
import unittest

from oslo_config import cfg

from aprsd.conf import common


class TestRateLimitPeriodOptions(unittest.TestCase):
    """A zero wait period must be refused at startup, not on every send.

    A zero-second period makes the rate limiter raise ValueError inside the
    send path, so every packet send fails (see #319).
    """

    def parse(self, name, value):
        with tempfile.NamedTemporaryFile('w', suffix='.conf') as f:
            f.write(f'[DEFAULT]\nowner_callsign = N0CALL\n{name} = {value}\n')
            f.flush()
            conf = cfg.ConfigOpts()
            conf.register_opts(common.aprsd_opts)
            conf(['--config-file', f.name])
            # oslo validates min/max when the value is read, not on parse.
            getattr(conf, name)
        return conf

    def test_zero_period_rejected_at_startup(self):
        for name in ('msg_rate_limit_period', 'ack_rate_limit_period'):
            with self.subTest(name=name):
                with self.assertRaises(cfg.ConfigFileValueError):
                    self.parse(name, 0)

    def test_positive_period_accepted(self):
        conf = self.parse('msg_rate_limit_period', 5)
        self.assertEqual(conf.msg_rate_limit_period, 5)
