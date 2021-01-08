import sys
import unittest

from aprsd import email

if sys.version_info >= (3, 2):
    from unittest import mock
else:
    from unittest import mock


class TestMain(unittest.TestCase):
    @mock.patch("aprsd.email._imap_connect")
    @mock.patch("aprsd.email._smtp_connect")
    def test_validate_email(self, imap_mock, smtp_mock):
        """Test to make sure we fail."""
        imap_mock.return_value = None
        smtp_mock.return_value = {"smaiof": "fire"}
        config = mock.MagicMock()

        email.validate_email_config(config, True)
