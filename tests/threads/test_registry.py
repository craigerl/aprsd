import unittest
from unittest import mock

from oslo_config import cfg

from aprsd.threads.registry import APRSRegistryThread

CONF = cfg.CONF


class TestAPRSRegistryThread(unittest.TestCase):
    """Unit tests for the APRSRegistryThread class."""

    def setUp(self):
        """Set up test fixtures."""
        CONF.aprs_registry.registry_url = 'https://registry.example.com/api/v1/registry'
        CONF.aprs_registry.description = 'Test APRSD instance'
        CONF.aprs_registry.service_website = None
        CONF.aprs_registry.frequency_seconds = 3600
        CONF.callsign = 'W1AW'
        CONF.owner_callsign = 'W1AW'

    @mock.patch('aprsd.threads.registry.requests.post')
    def test_loop_posts_registry_info(self, mock_post):
        """loop() posts the registry info to the configured URL."""
        thread = APRSRegistryThread()
        thread.wait = mock.Mock(return_value=False)

        result = thread.loop()

        self.assertTrue(result)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(args[0], CONF.aprs_registry.registry_url)
        self.assertIn('json', kwargs)
        self.assertEqual(kwargs['json']['callsign'], 'W1AW')

    @mock.patch('aprsd.threads.registry.requests.post')
    def test_loop_post_uses_timeout(self, mock_post):
        """The registry HTTP POST must use an explicit timeout.

        Without a timeout, a hung registry server blocks the thread's
        loop() for as long as the OS connection timeout allows, stalling
        the registry heartbeat indefinitely.
        """
        thread = APRSRegistryThread()
        thread.wait = mock.Mock(return_value=False)

        result = thread.loop()

        self.assertTrue(result)
        args, kwargs = mock_post.call_args
        self.assertIn('timeout', kwargs)
        self.assertIsInstance(kwargs['timeout'], (int, float))
        self.assertGreater(kwargs['timeout'], 0)

    @mock.patch('aprsd.threads.registry.requests.post')
    def test_loop_post_exception_logged(self, mock_post):
        """A failed POST is logged and does not kill the thread loop."""
        from aprsd.threads.registry import LOG

        mock_post.side_effect = Exception('Connection refused')
        thread = APRSRegistryThread()
        thread.wait = mock.Mock(return_value=False)

        with mock.patch.object(LOG, 'error') as mock_log_error:
            result = thread.loop()

        self.assertTrue(result)
        mock_log_error.assert_called()
