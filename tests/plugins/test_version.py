from unittest import mock

import aprsd
from aprsd.plugins import version as version_plugin

from .. import fake, test_plugin


class TestVersionPlugin(test_plugin.TestPlugin):
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
