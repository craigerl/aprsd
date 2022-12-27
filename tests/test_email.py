import unittest

from oslo_config import cfg

from aprsd import conf  # noqa: F401
from aprsd.plugins import email


CONF = cfg.CONF


class TestEmail(unittest.TestCase):
    def test_get_email_from_shortcut(self):
        CONF.email_plugin.shortcuts = None
        email_address = "something@something.com"
        addr = f"-{email_address}"
        actual = email.get_email_from_shortcut(addr)
        self.assertEqual(addr, actual)

        CONF.email_plugin.shortcuts = None
        actual = email.get_email_from_shortcut(addr)
        self.assertEqual(addr, actual)

        CONF.email_plugin.shortcuts = None
        actual = email.get_email_from_shortcut(addr)
        self.assertEqual(addr, actual)

        CONF.email_plugin.email_shortcuts = ["wb=something@something.com"]
        email.shortcuts_dict = None
        short = "wb"
        actual = email.get_email_from_shortcut(short)
        self.assertEqual(email_address, actual)
