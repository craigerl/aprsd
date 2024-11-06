import unittest
from unittest import mock

from aprsd.client.factory import Client, ClientFactory


class MockClient:
    """Mock client for testing."""

    @classmethod
    def is_enabled(cls):
        return True

    @classmethod
    def is_configured(cls):
        return True


class TestClientFactory(unittest.TestCase):
    """Test cases for ClientFactory."""

    def setUp(self):
        """Set up test fixtures."""
        self.factory = ClientFactory()
        # Clear any registered clients from previous tests
        self.factory.clients = []

    def test_singleton(self):
        """Test that ClientFactory is a singleton."""
        factory2 = ClientFactory()
        self.assertEqual(self.factory, factory2)

    def test_register_client(self):
        """Test registering a client."""
        self.factory.register(MockClient)
        self.assertIn(MockClient, self.factory.clients)

    def test_register_invalid_client(self):
        """Test registering an invalid client raises error."""
        invalid_client = mock.MagicMock(spec=Client)
        with self.assertRaises(ValueError):
            self.factory.register(invalid_client)

    def test_create_client(self):
        """Test creating a client."""
        self.factory.register(MockClient)
        client = self.factory.create()
        self.assertIsInstance(client, MockClient)

    def test_create_no_clients(self):
        """Test creating a client with no registered clients."""
        with self.assertRaises(Exception):
            self.factory.create()

    def test_is_client_enabled(self):
        """Test checking if any client is enabled."""
        self.factory.register(MockClient)
        self.assertTrue(self.factory.is_client_enabled())

    def test_is_client_enabled_none(self):
        """Test checking if any client is enabled when none are."""
        MockClient.is_enabled = classmethod(lambda cls: False)
        self.factory.register(MockClient)
        self.assertFalse(self.factory.is_client_enabled())

    def test_is_client_configured(self):
        """Test checking if any client is configured."""
        self.factory.register(MockClient)
        self.assertTrue(self.factory.is_client_configured())

    def test_is_client_configured_none(self):
        """Test checking if any client is configured when none are."""
        MockClient.is_configured = classmethod(lambda cls: False)
        self.factory.register(MockClient)
        self.assertFalse(self.factory.is_client_configured())
