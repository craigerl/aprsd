from unittest import mock

from oslo_config import cfg

import aprsd
from aprsd.client.drivers.fake import APRSDFakeDriver
from aprsd.plugins import version as version_plugin

from .. import fake, test_plugin

CONF = cfg.CONF


class TestVersionPlugin(test_plugin.TestPlugin):
    def setUp(self):
        # make sure the fake client driver is enabled
        # Mock CONF for testing
        super().setUp()
        self.conf_patcher = mock.patch('aprsd.client.drivers.fake.CONF')
        self.mock_conf = self.conf_patcher.start()

        # Configure fake_client.enabled
        self.mock_conf.fake_client.enabled = True

        # Create an instance of the driver
        self.driver = APRSDFakeDriver()
        self.fromcall = fake.FAKE_FROM_CALLSIGN

    def tearDown(self):
        self.conf_patcher.stop()
        super().tearDown()

    @mock.patch('aprsd.stats.collector.Collector')
    def test_version(self, mock_collector_class):
        # Set up the mock collector instance
        mock_collector_instance = mock_collector_class.return_value
        mock_collector_instance.collect.return_value = {
            'APRSDStats': {
                'uptime': '00:00:00',
            }
        }

        expected = f'APRSD ver:{aprsd.__version__} uptime:00:00:00'
        CONF.callsign = fake.FAKE_TO_CALLSIGN
        version = version_plugin.VersionPlugin()
        version.enabled = True

        packet = fake.fake_packet(
            message='No',
            msg_number=1,
        )

        actual = version.filter(packet)
        self.assertEqual(None, actual)

        packet = fake.fake_packet(
            message='version',
            msg_number=1,
        )
        actual = version.filter(packet)
        self.assertEqual(expected, actual)

        # Verify the mock was called exactly once
        mock_collector_instance.collect.assert_called_once()
