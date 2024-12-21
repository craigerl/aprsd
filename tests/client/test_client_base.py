import unittest
from unittest import mock

from aprsd.client.base import APRSClient
from aprsd.packets import core


class MockAPRSClient(APRSClient):
    """Concrete implementation of APRSClient for testing."""

    def stats(self):
        return {"packets_received": 0, "packets_sent": 0}

    def setup_connection(self):
        mock_connection = mock.MagicMock()
        # Configure the mock with required methods
        mock_connection.close = mock.MagicMock()
        mock_connection.stop = mock.MagicMock()
        mock_connection.set_filter = mock.MagicMock()
        mock_connection.send = mock.MagicMock()
        self._client = mock_connection
        return mock_connection

    def decode_packet(self, *args, **kwargs):
        return mock.MagicMock()

    def consumer(self, callback, blocking=False, immortal=False, raw=False):
        pass

    def is_alive(self):
        return True

    def close(self):
        pass

    @staticmethod
    def is_enabled():
        return True

    @staticmethod
    def transport():
        return "mock"

    def reset(self):
        """Mock implementation of reset."""
        if self._client:
            self._client.close()
        self._client = self.setup_connection()
        if self.filter:
            self._client.set_filter(self.filter)


class TestAPRSClient(unittest.TestCase):
    def setUp(self):
        # Reset the singleton instance before each test
        APRSClient._instance = None
        APRSClient._client = None
        self.client = MockAPRSClient()

    def test_singleton_pattern(self):
        """Test that multiple instantiations return the same instance."""
        client1 = MockAPRSClient()
        client2 = MockAPRSClient()
        self.assertIs(client1, client2)

    def test_set_filter(self):
        """Test setting APRS filter."""
        # Get the existing mock client that was created in __init__
        mock_client = self.client._client

        test_filter = "m/50"
        self.client.set_filter(test_filter)
        self.assertEqual(self.client.filter, test_filter)
        # The filter is set once during set_filter() and once during reset()
        mock_client.set_filter.assert_called_with(test_filter)

    @mock.patch("aprsd.client.base.LOG")
    def test_reset(self, mock_log):
        """Test client reset functionality."""
        # Create a new mock client with the necessary methods
        old_client = mock.MagicMock()
        self.client._client = old_client

        self.client.reset()

        # Verify the old client was closed
        old_client.close.assert_called_once()

        # Verify a new client was created
        self.assertIsNotNone(self.client._client)
        self.assertNotEqual(old_client, self.client._client)

    def test_send_packet(self):
        """Test sending an APRS packet."""
        mock_packet = mock.Mock(spec=core.Packet)
        self.client.send(mock_packet)
        self.client._client.send.assert_called_once_with(mock_packet)

    def test_stop(self):
        """Test stopping the client."""
        # Ensure client is created first
        self.client._create_client()

        self.client.stop()
        self.client._client.stop.assert_called_once()

    @mock.patch("aprsd.client.base.LOG")
    def test_create_client_failure(self, mock_log):
        """Test handling of client creation failure."""
        # Make setup_connection raise an exception
        with mock.patch.object(
            self.client,
            "setup_connection",
            side_effect=Exception("Connection failed"),
        ):
            with self.assertRaises(Exception):
                self.client._create_client()

            self.assertIsNone(self.client._client)
            mock_log.error.assert_called_once()

    def test_client_property(self):
        """Test the client property creates client if none exists."""
        self.client._client = None
        client = self.client.client
        self.assertIsNotNone(client)

    def test_filter_applied_on_creation(self):
        """Test that filter is applied when creating new client."""
        test_filter = "m/50"
        self.client.set_filter(test_filter)

        # Force client recreation
        self.client.reset()

        # Verify filter was applied to new client
        self.client._client.set_filter.assert_called_with(test_filter)


if __name__ == "__main__":
    unittest.main()
