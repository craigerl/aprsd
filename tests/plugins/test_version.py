from oslo_config import cfg

import aprsd
from aprsd.plugins import version as version_plugin

from .. import fake, test_plugin


CONF = cfg.CONF


class TestVersionPlugin(test_plugin.TestPlugin):

    def test_version(self):
        expected = f"APRSD ver:{aprsd.__version__} uptime:00:00:00"
        CONF.callsign = fake.FAKE_TO_CALLSIGN
        version = version_plugin.VersionPlugin()
        version.enabled = True

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
