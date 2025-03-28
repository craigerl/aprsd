import unittest
from unittest import mock

from aprsd.client.drivers.registry import DriverRegistry

from ..mock_client_driver import MockClientDriver


class TestDriverRegistry(unittest.TestCase):
    """Unit tests for the DriverRegistry class."""

    def setUp(self):
        # Reset the singleton instance before each test
        DriverRegistry._singleton_instances = {}
        self.registry = DriverRegistry()
        self.registry.drivers = []

        # Mock APRSISDriver completely
        self.aprsis_patcher = mock.patch('aprsd.client.drivers.aprsis.APRSISDriver')
        mock_aprsis_class = self.aprsis_patcher.start()
        mock_aprsis_class.is_enabled.return_value = False
        mock_aprsis_class.is_configured.return_value = False

        # Mock the instance methods as well
        mock_instance = mock_aprsis_class.return_value
        mock_instance.is_enabled.return_value = False
        mock_instance.is_configured.return_value = False

        # Mock CONF to prevent password check
        self.conf_patcher = mock.patch('aprsd.client.drivers.aprsis.CONF')
        mock_conf = self.conf_patcher.start()
        mock_conf.aprs_network.password = 'dummy'
        mock_conf.aprs_network.login = 'dummy'

    def tearDown(self):
        # Reset the singleton instance after each test
        DriverRegistry().drivers = []
        self.aprsis_patcher.stop()
        self.conf_patcher.stop()

    def test_get_driver_with_valid_driver(self):
        """Test getting an enabled and configured driver."""
        # Add an enabled and configured driver
        driver = MockClientDriver
        driver.is_enabled = mock.MagicMock(return_value=True)
        driver.is_configured = mock.MagicMock(return_value=True)
        self.registry.register(MockClientDriver)

        # Get the driver
        result = self.registry.get_driver()
        print(result)
        self.assertTrue(isinstance(result, MockClientDriver))

    def test_get_driver_with_disabled_driver(self):
        """Test getting a driver when only disabled drivers exist."""
        driver = MockClientDriver
        driver.is_enabled = mock.MagicMock(return_value=False)
        driver.is_configured = mock.MagicMock(return_value=False)
        self.registry.register(driver)

        with self.assertRaises(ValueError) as context:
            self.registry.get_driver()
        self.assertIn('No enabled driver found', str(context.exception))

    def test_get_driver_with_unconfigured_driver(self):
        """Test getting a driver when only unconfigured drivers exist."""
        driver = MockClientDriver
        driver.is_enabled = mock.MagicMock(return_value=True)
        driver.is_configured = mock.MagicMock(return_value=False)
        self.registry.register(driver)

        with self.assertRaises(ValueError) as context:
            self.registry.get_driver()
        self.assertIn('No enabled driver found', str(context.exception))

    def test_get_driver_with_no_drivers(self):
        """Test getting a driver when no drivers exist."""
        # Try to get a driver
        with self.assertRaises(ValueError) as context:
            self.registry.get_driver()
        self.assertIn('No enabled driver found', str(context.exception))

    def test_get_driver_with_multiple_drivers(self):
        """Test getting a driver when multiple valid drivers exist."""
        # Add multiple drivers
        driver1 = MockClientDriver
        driver1.is_enabled = mock.MagicMock(return_value=True)
        driver1.is_configured = mock.MagicMock(return_value=True)
        driver2 = MockClientDriver
        self.registry.register(driver1)
        self.registry.register(driver2)

        # Get the driver - should return the first one
        result = self.registry.get_driver()
        # We can only check that it's a MockDriver instance
        self.assertTrue(isinstance(result, MockClientDriver))


if __name__ == '__main__':
    unittest.main()
