import datetime
import unittest
from unittest import mock

from aprslib.exceptions import LoginError

from aprsd import exception
from aprsd.client.drivers.aprsis import APRSISDriver
from aprsd.client.drivers.registry import ClientDriver
from aprsd.packets import core


class TestAPRSISDriver(unittest.TestCase):
    """Unit tests for the APRSISDriver class."""

    def setUp(self):
        # Mock configuration
        self.conf_patcher = mock.patch('aprsd.client.drivers.aprsis.CONF')
        self.mock_conf = self.conf_patcher.start()

        # Configure APRS-IS settings
        self.mock_conf.aprs_network.enabled = True
        self.mock_conf.aprs_network.login = 'TEST'
        self.mock_conf.aprs_network.password = '12345'
        self.mock_conf.aprs_network.host = 'rotate.aprs.net'
        self.mock_conf.aprs_network.port = 14580

        # Mock APRS Lib Client
        self.aprslib_patcher = mock.patch('aprsd.client.drivers.aprsis.APRSLibClient')
        self.mock_aprslib = self.aprslib_patcher.start()
        self.mock_client = mock.MagicMock()
        self.mock_aprslib.return_value = self.mock_client

        # Create an instance of the driver
        self.driver = APRSISDriver()

    def tearDown(self):
        self.conf_patcher.stop()
        self.aprslib_patcher.stop()

    def test_implements_client_driver_protocol(self):
        """Test that APRSISDriver implements the ClientDriver Protocol."""
        # Verify the instance is recognized as implementing the Protocol
        self.assertIsInstance(self.driver, ClientDriver)

        # Verify all required methods are present with correct signatures
        required_methods = [
            'is_enabled',
            'is_configured',
            'is_alive',
            'close',
            'send',
            'setup_connection',
            'set_filter',
            'login_success',
            'login_failure',
            'consumer',
            'decode_packet',
            'stats',
        ]

        for method_name in required_methods:
            self.assertTrue(
                hasattr(self.driver, method_name),
                f'Missing required method: {method_name}',
            )

    def test_init(self):
        """Test initialization sets default values."""
        self.assertIsInstance(self.driver.max_delta, datetime.timedelta)
        self.assertEqual(self.driver.max_delta, datetime.timedelta(minutes=2))
        self.assertFalse(self.driver.login_status['success'])
        self.assertIsNone(self.driver.login_status['message'])
        self.assertIsNone(self.driver._client)

    def test_is_enabled_true(self):
        """Test is_enabled returns True when APRS-IS is enabled."""
        self.mock_conf.aprs_network.enabled = True
        self.assertTrue(APRSISDriver.is_enabled())

    def test_is_enabled_false(self):
        """Test is_enabled returns False when APRS-IS is disabled."""
        self.mock_conf.aprs_network.enabled = False
        self.assertFalse(APRSISDriver.is_enabled())

    def test_is_enabled_key_error(self):
        """Test is_enabled returns False when enabled flag doesn't exist."""
        self.mock_conf.aprs_network = mock.MagicMock()
        type(self.mock_conf.aprs_network).enabled = mock.PropertyMock(
            side_effect=KeyError
        )
        self.assertFalse(APRSISDriver.is_enabled())

    def test_is_configured_true(self):
        """Test is_configured returns True when properly configured."""
        with mock.patch.object(APRSISDriver, 'is_enabled', return_value=True):
            self.mock_conf.aprs_network.login = 'TEST'
            self.mock_conf.aprs_network.password = '12345'
            self.mock_conf.aprs_network.host = 'rotate.aprs.net'

            self.assertTrue(APRSISDriver.is_configured())

    def test_is_configured_no_login(self):
        """Test is_configured raises exception when login not set."""
        with mock.patch.object(APRSISDriver, 'is_enabled', return_value=True):
            self.mock_conf.aprs_network.login = None

            with self.assertRaises(exception.MissingConfigOptionException):
                APRSISDriver.is_configured()

    def test_is_configured_no_password(self):
        """Test is_configured raises exception when password not set."""
        with mock.patch.object(APRSISDriver, 'is_enabled', return_value=True):
            self.mock_conf.aprs_network.login = 'TEST'
            self.mock_conf.aprs_network.password = None

            with self.assertRaises(exception.MissingConfigOptionException):
                APRSISDriver.is_configured()

    def test_is_configured_no_host(self):
        """Test is_configured raises exception when host not set."""
        with mock.patch.object(APRSISDriver, 'is_enabled', return_value=True):
            self.mock_conf.aprs_network.login = 'TEST'
            self.mock_conf.aprs_network.password = '12345'
            self.mock_conf.aprs_network.host = None

            with self.assertRaises(exception.MissingConfigOptionException):
                APRSISDriver.is_configured()

    def test_is_configured_disabled(self):
        """Test is_configured returns True when not enabled."""
        with mock.patch.object(APRSISDriver, 'is_enabled', return_value=False):
            self.assertTrue(APRSISDriver.is_configured())

    def test_is_alive_no_client(self):
        """Test is_alive returns False when no client."""
        self.driver._client = None
        self.assertFalse(self.driver.is_alive)

    def test_is_alive_true(self):
        """Test is_alive returns True when client is alive and connection is not stale."""
        self.driver._client = self.mock_client
        self.mock_client.is_alive.return_value = True

        with mock.patch.object(self.driver, '_is_stale_connection', return_value=False):
            self.assertTrue(self.driver.is_alive)

    def test_is_alive_client_not_alive(self):
        """Test is_alive returns False when client is not alive."""
        self.driver._client = self.mock_client
        self.mock_client.is_alive.return_value = False

        with mock.patch.object(self.driver, '_is_stale_connection', return_value=False):
            self.assertFalse(self.driver.is_alive)

    def test_is_alive_stale_connection(self):
        """Test is_alive returns False when connection is stale."""
        self.driver._client = self.mock_client
        self.mock_client.is_alive.return_value = True

        with mock.patch.object(self.driver, '_is_stale_connection', return_value=True):
            self.assertFalse(self.driver.is_alive)

    def test_close(self):
        """Test close method stops and closes the client."""
        self.driver._client = self.mock_client

        self.driver.close()

        self.mock_client.stop.assert_called_once()
        self.mock_client.close.assert_called_once()

    def test_close_no_client(self):
        """Test close method handles no client gracefully."""
        self.driver._client = None

        # Should not raise exception
        self.driver.close()

    def test_send(self):
        """Test send passes packet to client."""
        self.driver._client = self.mock_client
        mock_packet = mock.MagicMock(spec=core.Packet)

        self.driver.send(mock_packet)

        self.mock_client.send.assert_called_once_with(mock_packet)

    @mock.patch('aprsd.client.drivers.aprsis.LOG')
    def test_setup_connection_success(self, mock_log):
        """Test setup_connection successfully connects."""
        # Configure successful connection
        self.mock_client.server_string = 'Test APRS-IS Server'

        self.driver.setup_connection()

        # Check client created with correct parameters
        self.mock_aprslib.assert_called_once_with(
            self.mock_conf.aprs_network.login,
            passwd=self.mock_conf.aprs_network.password,
            host=self.mock_conf.aprs_network.host,
            port=self.mock_conf.aprs_network.port,
        )

        # Check logger set and connection initialized
        self.assertEqual(self.mock_client.logger, mock_log)
        self.mock_client.connect.assert_called_once()

        # Check status updated
        self.assertTrue(self.driver.connected)
        self.assertTrue(self.driver.login_status['success'])
        self.assertEqual(self.driver.login_status['message'], 'Test APRS-IS Server')

    @mock.patch('aprsd.client.drivers.aprsis.LOG')
    @mock.patch('aprsd.client.drivers.aprsis.time.sleep')
    def test_setup_connection_login_error(self, mock_sleep, mock_log):
        """Test setup_connection handles login error."""
        # Configure login error
        login_error = LoginError('Bad login')
        login_error.message = 'Invalid login credentials'
        self.mock_client.connect.side_effect = login_error

        self.driver.setup_connection()

        # Check error logged
        mock_log.error.assert_any_call("Failed to login to APRS-IS Server 'Bad login'")
        mock_log.error.assert_any_call('Invalid login credentials')

        # Check status updated
        self.assertFalse(self.driver.connected)
        self.assertFalse(self.driver.login_status['success'])
        self.assertEqual(
            self.driver.login_status['message'], 'Invalid login credentials'
        )

        # Check backoff used
        mock_sleep.assert_called()

    @mock.patch('aprsd.client.drivers.aprsis.LOG')
    @mock.patch('aprsd.client.drivers.aprsis.time.sleep')
    def test_setup_connection_general_error(self, mock_sleep, mock_log):
        """Test setup_connection handles general error."""
        # Configure general exception
        error_message = 'Connection error'
        error = Exception(error_message)
        # Standard exceptions don't have a message attribute
        self.mock_client.connect.side_effect = error

        self.driver.setup_connection()

        # Check error logged
        mock_log.error.assert_any_call(
            f"Unable to connect to APRS-IS server. '{error_message}' "
        )

        # Check status updated
        self.assertFalse(self.driver.connected)
        self.assertFalse(self.driver.login_status['success'])

        # Check login message contains the error message (more flexible than exact equality)
        self.assertIn(error_message, self.driver.login_status['message'])

        # Check backoff used
        mock_sleep.assert_called()

    def test_set_filter(self):
        """Test set_filter passes filter to client."""
        self.driver._client = self.mock_client
        test_filter = 'm/50'

        self.driver.set_filter(test_filter)

        self.mock_client.set_filter.assert_called_once_with(test_filter)

    def test_login_success(self):
        """Test login_success returns login status."""
        self.driver.login_status['success'] = True
        self.assertTrue(self.driver.login_success())

        self.driver.login_status['success'] = False
        self.assertFalse(self.driver.login_success())

    def test_login_failure(self):
        """Test login_failure returns error message."""
        self.driver.login_status['message'] = None
        self.assertIsNone(self.driver.login_failure())

        self.driver.login_status['message'] = 'Test error'
        self.assertEqual(self.driver.login_failure(), 'Test error')

    def test_filter_property(self):
        """Test filter property returns client filter."""
        self.driver._client = self.mock_client
        test_filter = 'm/50'
        self.mock_client.filter = test_filter

        self.assertEqual(self.driver.filter, test_filter)

    def test_server_string_property(self):
        """Test server_string property returns client server string."""
        self.driver._client = self.mock_client
        test_string = 'Test APRS-IS Server'
        self.mock_client.server_string = test_string

        self.assertEqual(self.driver.server_string, test_string)

    def test_keepalive_property(self):
        """Test keepalive property returns client keepalive."""
        self.driver._client = self.mock_client
        test_time = datetime.datetime.now()
        self.mock_client.aprsd_keepalive = test_time

        self.assertEqual(self.driver.keepalive, test_time)

    @mock.patch('aprsd.client.drivers.aprsis.LOG')
    def test_is_stale_connection_true(self, mock_log):
        """Test _is_stale_connection returns True when connection is stale."""
        self.driver._client = self.mock_client
        # Set keepalive to 3 minutes ago (exceeds max_delta of 2 minutes)
        self.mock_client.aprsd_keepalive = datetime.datetime.now() - datetime.timedelta(
            minutes=3
        )

        result = self.driver._is_stale_connection()

        self.assertTrue(result)
        mock_log.error.assert_called_once()

    def test_is_stale_connection_false(self):
        """Test _is_stale_connection returns False when connection is not stale."""
        self.driver._client = self.mock_client
        # Set keepalive to 1 minute ago (within max_delta of 2 minutes)
        self.mock_client.aprsd_keepalive = datetime.datetime.now() - datetime.timedelta(
            minutes=1
        )

        result = self.driver._is_stale_connection()

        self.assertFalse(result)

    def test_transport(self):
        """Test transport returns appropriate transport type."""
        self.assertEqual(APRSISDriver.transport(), 'aprsis')

    def test_decode_packet(self):
        """Test decode_packet uses core.factory."""
        with mock.patch('aprsd.client.drivers.aprsis.core.factory') as mock_factory:
            raw_packet = {'from': 'TEST', 'to': 'APRS'}
            self.driver.decode_packet(raw_packet)
            mock_factory.assert_called_once_with(raw_packet)

    @mock.patch('aprsd.client.drivers.aprsis.LOG')
    def test_consumer_success(self, mock_log):
        """Test consumer forwards callback to client."""
        self.driver._client = self.mock_client
        mock_callback = mock.MagicMock()

        self.driver.consumer(mock_callback, raw=True)

        self.mock_client.consumer.assert_called_once_with(
            mock_callback, blocking=False, immortal=False, raw=True
        )

    @mock.patch('aprsd.client.drivers.aprsis.LOG')
    def test_consumer_exception(self, mock_log):
        """Test consumer handles exceptions."""
        self.driver._client = self.mock_client
        mock_callback = mock.MagicMock()
        test_error = Exception('Test error')
        self.mock_client.consumer.side_effect = test_error

        with self.assertRaises(Exception):  # noqa: B017
            self.driver.consumer(mock_callback)

        mock_log.error.assert_called_with(test_error)

    @mock.patch('aprsd.client.drivers.aprsis.LOG')
    def test_consumer_no_client(self, mock_log):
        """Test consumer handles no client gracefully."""
        self.driver._client = None
        mock_callback = mock.MagicMock()

        self.driver.consumer(mock_callback)

        mock_log.warning.assert_called_once()
        self.assertFalse(self.driver.connected)

    def test_stats_configured_with_client(self):
        """Test stats returns correct data when configured with client."""
        # Configure driver
        with mock.patch.object(self.driver, 'is_configured', return_value=True):
            self.driver._client = self.mock_client
            self.mock_client.aprsd_keepalive = datetime.datetime.now()
            self.mock_client.server_string = 'Test Server'
            self.mock_client.filter = 'm/50'

            stats = self.driver.stats()

            self.assertEqual(stats['connected'], True)
            self.assertEqual(stats['filter'], 'm/50')
            self.assertEqual(stats['server_string'], 'Test Server')
            self.assertEqual(stats['transport'], 'aprsis')

    def test_stats_serializable(self):
        """Test stats with serializable=True converts datetime to ISO format."""
        # Configure driver
        with mock.patch.object(self.driver, 'is_configured', return_value=True):
            self.driver._client = self.mock_client
            test_time = datetime.datetime.now()
            self.mock_client.aprsd_keepalive = test_time

            stats = self.driver.stats(serializable=True)

            # Check keepalive is a string in ISO format
            self.assertIsInstance(stats['connection_keepalive'], str)
            # Try parsing it to verify it's a valid ISO format
            try:
                datetime.datetime.fromisoformat(stats['connection_keepalive'])
            except ValueError:
                self.fail('keepalive is not in valid ISO format')

    def test_stats_no_client(self):
        """Test stats with no client."""
        with mock.patch.object(self.driver, 'is_configured', return_value=True):
            self.driver._client = None

            stats = self.driver.stats()

            self.assertEqual(stats['connection_keepalive'], 'None')
            self.assertEqual(stats['server_string'], 'None')

    def test_stats_not_configured(self):
        """Test stats when not configured returns empty dict."""
        with mock.patch.object(self.driver, 'is_configured', return_value=False):
            stats = self.driver.stats()
            self.assertEqual(stats, {})


if __name__ == '__main__':
    unittest.main()
