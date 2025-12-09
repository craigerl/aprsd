import unittest
from unittest import mock

from aprsd.client.client import APRSDClient
from aprsd.client.drivers.registry import DriverRegistry
from aprsd.packets import core
from tests.mock_client_driver import MockClientDriver


class TestAPRSDClient(unittest.TestCase):
    """Unit tests for the APRSDClient class."""

    def setUp(self):
        """Set up test fixtures."""
        # Reset singleton instances
        APRSDClient._instance = None
        APRSDClient.driver = None
        # Reset DriverRegistry singleton - the singleton decorator stores instance here
        DriverRegistry.instance = None

        # Mock APRSISDriver to prevent it from being checked
        self.aprsis_patcher = mock.patch('aprsd.client.drivers.aprsis.APRSISDriver')
        mock_aprsis_class = self.aprsis_patcher.start()
        mock_aprsis_class.is_enabled.return_value = False
        mock_aprsis_class.is_configured.return_value = False

        self.mock_driver = MockClientDriver()
        # Create a mock registry instance
        mock_registry_instance = mock.MagicMock()
        mock_registry_instance.get_driver.return_value = self.mock_driver
        # Patch DriverRegistry to return our mock instance
        self.registry_patcher = mock.patch(
            'aprsd.client.client.DriverRegistry', return_value=mock_registry_instance
        )
        self.mock_registry = self.registry_patcher.start()

    def tearDown(self):
        """Clean up after tests."""
        if hasattr(APRSDClient, '_instance'):
            if APRSDClient._instance:
                APRSDClient._instance.close()
            APRSDClient._instance = None
        APRSDClient.driver = None
        self.registry_patcher.stop()
        self.aprsis_patcher.stop()

    def test_singleton_pattern(self):
        """Test that APRSDClient is a singleton."""
        client1 = APRSDClient(auto_connect=False)
        client2 = APRSDClient(auto_connect=False)
        self.assertIs(client1, client2)
        self.assertEqual(id(client1), id(client2))

    def test_init_with_auto_connect(self):
        """Test initialization with auto_connect=True."""
        client = APRSDClient(auto_connect=True)
        # Should have called setup_connection
        self.assertIsNotNone(client.driver)

    def test_init_without_auto_connect(self):
        """Test initialization with auto_connect=False."""
        client = APRSDClient(auto_connect=False)
        self.assertIsNotNone(client.driver)
        self.assertFalse(client.connected)

    def test_stats(self):
        """Test stats() method."""
        client = APRSDClient(auto_connect=False)
        stats = client.stats()
        self.assertIsInstance(stats, dict)

        stats_serializable = client.stats(serializable=True)
        self.assertIsInstance(stats_serializable, dict)

    def test_stats_no_driver(self):
        """Test stats() when driver is None."""
        client = APRSDClient(auto_connect=False)
        client.driver = None
        stats = client.stats()
        self.assertEqual(stats, {})

    def test_is_enabled(self):
        """Test is_enabled() static method."""
        # Stop the registry patcher temporarily to use real registry
        self.registry_patcher.stop()
        try:
            # Reset singleton
            DriverRegistry.instance = None
            registry = DriverRegistry()
            mock_driver_class = mock.MagicMock()
            mock_driver_class.is_enabled.return_value = True
            registry.drivers = [mock_driver_class]

            result = APRSDClient.is_enabled()
            self.assertTrue(result)
        finally:
            # Restart the patcher
            self.registry_patcher.start()

    def test_is_enabled_no_drivers(self):
        """Test is_enabled() with no drivers."""
        # Stop the registry patcher temporarily to use real registry
        self.registry_patcher.stop()
        try:
            # Reset singleton
            DriverRegistry.instance = None
            registry = DriverRegistry()
            registry.drivers = []

            result = APRSDClient.is_enabled()
            self.assertFalse(result)
        finally:
            # Restart the patcher
            self.registry_patcher.start()

    def test_is_configured(self):
        """Test is_configured() static method."""
        # Stop the registry patcher temporarily to use real registry
        self.registry_patcher.stop()
        try:
            # Reset singleton
            DriverRegistry.instance = None
            registry = DriverRegistry()
            mock_driver_class = mock.MagicMock()
            mock_driver_class.is_enabled.return_value = True
            mock_driver_class.is_configured.return_value = True
            registry.drivers = [mock_driver_class]

            result = APRSDClient.is_configured()
            self.assertTrue(result)
        finally:
            # Restart the patcher
            self.registry_patcher.start()

    def test_is_configured_no_drivers(self):
        """Test is_configured() with no drivers."""
        # Stop the registry patcher temporarily to use real registry
        self.registry_patcher.stop()
        try:
            # Reset singleton
            DriverRegistry.instance = None
            registry = DriverRegistry()
            registry.drivers = []

            result = APRSDClient.is_configured()
            self.assertFalse(result)
        finally:
            # Restart the patcher
            self.registry_patcher.start()

    def test_login_success_property(self):
        """Test login_success property."""
        client = APRSDClient(auto_connect=False)
        self.mock_driver.login_status['success'] = True
        self.assertTrue(client.login_success)

        self.mock_driver.login_status['success'] = False
        self.assertFalse(client.login_success)

    def test_login_success_no_driver(self):
        """Test login_success property when driver is None."""
        client = APRSDClient(auto_connect=False)
        client.driver = None
        self.assertFalse(client.login_success)

    def test_login_failure_property(self):
        """Test login_failure property."""
        client = APRSDClient(auto_connect=False)
        self.mock_driver.login_status['message'] = 'Test failure'
        self.assertEqual(client.login_failure, 'Test failure')

    def test_login_failure_no_driver(self):
        """Test login_failure property when driver is None."""
        client = APRSDClient(auto_connect=False)
        client.driver = None
        self.assertIsNone(client.login_failure)

    def test_set_filter(self):
        """Test set_filter() method."""
        client = APRSDClient(auto_connect=False)
        filter_str = 'test filter'
        client.set_filter(filter_str)
        self.assertEqual(client.filter, filter_str)
        self.assertEqual(self.mock_driver.filter, filter_str)

    def test_set_filter_no_driver(self):
        """Test set_filter() when driver is None."""
        client = APRSDClient(auto_connect=False)
        client.driver = None
        filter_str = 'test filter'
        client.set_filter(filter_str)
        self.assertEqual(client.filter, filter_str)

    def test_get_filter(self):
        """Test get_filter() method."""
        client = APRSDClient(auto_connect=False)
        filter_str = 'test filter'
        client.set_filter(filter_str)
        # get_filter returns driver.filter, not client.filter
        self.mock_driver.filter = filter_str
        result = client.get_filter()
        self.assertEqual(result, filter_str)

    def test_get_filter_no_driver(self):
        """Test get_filter() when driver is None."""
        client = APRSDClient(auto_connect=False)
        client.driver = None
        result = client.get_filter()
        self.assertIsNone(result)

    def test_is_alive(self):
        """Test is_alive() method."""
        client = APRSDClient(auto_connect=False)
        self.mock_driver._alive = True
        self.assertTrue(client.is_alive())

        self.mock_driver._alive = False
        self.assertFalse(client.is_alive())

    def test_connect(self):
        """Test connect() method."""
        client = APRSDClient(auto_connect=False)
        self.assertFalse(client.connected)
        # Make sure driver.is_alive returns True after setup_connection
        self.mock_driver._alive = True
        client.connect()
        self.assertTrue(client.connected)
        self.assertTrue(client.running)

    def test_connect_already_connected(self):
        """Test connect() when already connected."""
        client = APRSDClient(auto_connect=False)
        client.connected = True
        client.connect()
        # Should still be connected
        self.assertTrue(client.connected)

    def test_connect_no_driver(self):
        """Test connect() when driver is None."""
        client = APRSDClient(auto_connect=False)
        client.driver = None
        client.connect()
        # Should get a driver from registry
        self.assertIsNotNone(client.driver)

    def test_close(self):
        """Test close() method."""
        client = APRSDClient(auto_connect=False)
        client.connected = True
        client.running = True
        client.close()
        self.assertFalse(client.connected)
        self.assertFalse(client.running)
        self.mock_driver.close.assert_called()

    def test_close_no_driver(self):
        """Test close() when driver is None."""
        client = APRSDClient(auto_connect=False)
        client.driver = None
        client.connected = True
        client.close()
        self.assertFalse(client.connected)

    def test_reset(self):
        """Test reset() method."""
        client = APRSDClient(auto_connect=False)
        client.connected = True
        client.filter = 'test filter'
        client.auto_connect = True

        client.reset()
        self.mock_driver.close.assert_called()
        self.mock_driver.setup_connection.assert_called()
        self.mock_driver.set_filter.assert_called_with('test filter')

    def test_reset_no_driver(self):
        """Test reset() when driver is None."""
        client = APRSDClient(auto_connect=False)
        client.driver = None
        # Should not raise exception
        client.reset()

    def test_reset_no_auto_connect(self):
        """Test reset() with auto_connect=False."""
        client = APRSDClient(auto_connect=False)
        client.auto_connect = False
        client.reset()
        self.mock_driver.close.assert_called()
        # Should not call setup_connection
        self.mock_driver.setup_connection.assert_not_called()

    def test_send(self):
        """Test send() method."""
        client = APRSDClient(auto_connect=False)
        client.running = True
        packet = mock.MagicMock(spec=core.Packet)

        result = client.send(packet)
        self.assertTrue(result)
        self.mock_driver.send.assert_called_with(packet)

    def test_send_not_running(self):
        """Test send() when not running."""
        client = APRSDClient(auto_connect=False)
        client.running = False
        packet = mock.MagicMock(spec=core.Packet)

        result = client.send(packet)
        self.assertFalse(result)
        self.mock_driver.send.assert_not_called()

    def test_consumer(self):
        """Test consumer() method."""
        client = APRSDClient(auto_connect=False)
        client.running = True
        callback = mock.MagicMock()

        client.consumer(callback, raw=True)
        self.mock_driver.consumer.assert_called_with(callback=callback, raw=True)

    def test_consumer_not_running(self):
        """Test consumer() when not running."""
        client = APRSDClient(auto_connect=False)
        client.running = False
        callback = mock.MagicMock()

        result = client.consumer(callback)
        self.assertIsNone(result)
        self.mock_driver.consumer.assert_not_called()

    def test_decode_packet(self):
        """Test decode_packet() method."""
        client = APRSDClient(auto_connect=False)
        packet = mock.MagicMock(spec=core.Packet)
        # Configure the side_effect to return our packet
        self.mock_driver.decode_packet.side_effect = lambda *args, **kwargs: packet

        result = client.decode_packet(frame='test')
        self.assertEqual(result, packet)
        self.mock_driver.decode_packet.assert_called_with(frame='test')

    def test_decode_packet_exception(self):
        """Test decode_packet() with exception."""
        client = APRSDClient(auto_connect=False)
        self.mock_driver.decode_packet.side_effect = Exception('Decode error')

        result = client.decode_packet(frame='test')
        self.assertIsNone(result)

    def test_keepalive_check(self):
        """Test keepalive_check() method."""
        client = APRSDClient(auto_connect=False)
        client._checks = False
        self.mock_driver._alive = True

        # First check should not reset
        with mock.patch.object(client, 'reset') as mock_reset:
            client.keepalive_check()
            self.assertTrue(client._checks)
            mock_reset.assert_not_called()

        # Second check with dead driver should reset
        self.mock_driver._alive = False
        with mock.patch.object(client, 'reset') as mock_reset:
            client.keepalive_check()
            mock_reset.assert_called()

    def test_keepalive_log(self):
        """Test keepalive_log() method."""
        import datetime

        client = APRSDClient(auto_connect=False)
        self.mock_driver._keepalive = datetime.datetime.now()

        with mock.patch('aprsd.client.client.LOGU') as mock_logu:
            client.keepalive_log()
            mock_logu.opt.assert_called()

    def test_keepalive_log_no_keepalive(self):
        """Test keepalive_log() when keepalive is None."""
        client = APRSDClient(auto_connect=False)
        self.mock_driver._keepalive = None

        with mock.patch('aprsd.client.client.LOGU') as mock_logu:
            client.keepalive_log()
            mock_logu.opt.assert_called()
