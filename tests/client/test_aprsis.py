import datetime
import unittest
from unittest import mock

from aprsd import exception
from aprsd.client.aprsis import APRSISClient


class TestAPRSISClient(unittest.TestCase):
    """Test cases for APRSISClient."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()

        # Mock the config
        self.mock_conf = mock.MagicMock()
        self.mock_conf.aprs_network.enabled = True
        self.mock_conf.aprs_network.login = "TEST"
        self.mock_conf.aprs_network.password = "12345"
        self.mock_conf.aprs_network.host = "localhost"
        self.mock_conf.aprs_network.port = 14580

    @mock.patch("aprsd.client.base.APRSClient")
    @mock.patch("aprsd.client.drivers.aprsis.Aprsdis")
    def test_stats_not_configured(self, mock_aprsdis, mock_base):
        """Test stats when client is not configured."""
        mock_client = mock.MagicMock()
        mock_aprsdis.return_value = mock_client

        with mock.patch("aprsd.client.aprsis.cfg.CONF", self.mock_conf):
            self.client = APRSISClient()

        with mock.patch.object(APRSISClient, "is_configured", return_value=False):
            stats = self.client.stats()
            self.assertEqual({}, stats)

    @mock.patch("aprsd.client.base.APRSClient")
    @mock.patch("aprsd.client.drivers.aprsis.Aprsdis")
    def test_stats_configured(self, mock_aprsdis, mock_base):
        """Test stats when client is configured."""
        mock_client = mock.MagicMock()
        mock_aprsdis.return_value = mock_client

        with mock.patch("aprsd.client.aprsis.cfg.CONF", self.mock_conf):
            self.client = APRSISClient()

        mock_client = mock.MagicMock()
        mock_client.server_string = "test.server:14580"
        mock_client.aprsd_keepalive = datetime.datetime.now()
        self.client._client = mock_client
        self.client.filter = "m/50"

        with mock.patch.object(APRSISClient, "is_configured", return_value=True):
            stats = self.client.stats()
            from rich.console import Console

            c = Console()
            c.print(stats)
            self.assertEqual(
                {
                    "connected": True,
                    "filter": "m/50",
                    "login_status": {"message": mock.ANY, "success": True},
                    "connection_keepalive": mock_client.aprsd_keepalive,
                    "server_string": mock_client.server_string,
                    "transport": "aprsis",
                },
                stats,
            )

    def test_is_configured_missing_login(self):
        """Test is_configured with missing login."""
        self.mock_conf.aprs_network.login = None
        with self.assertRaises(exception.MissingConfigOptionException):
            APRSISClient.is_configured()

    def test_is_configured_missing_password(self):
        """Test is_configured with missing password."""
        self.mock_conf.aprs_network.password = None
        with self.assertRaises(exception.MissingConfigOptionException):
            APRSISClient.is_configured()

    def test_is_configured_missing_host(self):
        """Test is_configured with missing host."""
        self.mock_conf.aprs_network.host = None
        with mock.patch("aprsd.client.aprsis.cfg.CONF", self.mock_conf):
            with self.assertRaises(exception.MissingConfigOptionException):
                APRSISClient.is_configured()
