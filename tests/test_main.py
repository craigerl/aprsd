# -*- coding: utf-8 -*-
import sys
import unittest

import pytest

from aprsd import main

if sys.version_info >= (3, 2):
    from unittest import mock
else:
    import mock


class testMain(unittest.TestCase):
    @mock.patch("aprsd.main._imap_connect")
    @mock.patch("aprsd.main._smtp_connect")
    def test_validate_email(self, imap_mock, smtp_mock):
        """Test to make sure we fail."""
        imap_mock.return_value = None
        smtp_mock.return_value = {"smaiof": "fire"}

        main.validate_email()
