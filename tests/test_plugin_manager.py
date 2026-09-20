import unittest
from unittest import mock

from oslo_config import cfg

from aprsd import conf  # noqa: F401
from aprsd import plugin as aprsd_plugin

CONF = cfg.CONF


class TestPluginManagerCreateClass(unittest.TestCase):
    """Unit tests for PluginManager._create_class().

    _create_class() previously used assert statements to validate the
    module/class; asserts are stripped under `python -O`, silently
    skipping validation.  These tests guard the replacement explicit
    checks.
    """

    def setUp(self):
        """Set up test fixtures."""
        aprsd_plugin.PluginManager._instance = None
        self.pm = aprsd_plugin.PluginManager()
        self.pm._init()

    def test_missing_class_raises(self):
        """A fqn whose class does not exist must raise ImportError.

        This replaces an assert (stripped under `python -O`), so the
        failure is always detected.
        """
        with self.assertRaises(ImportError):
            self.pm._create_class(
                'aprsd.plugins.ping.NoSuchPluginClass',
                super_cls=aprsd_plugin.APRSDPluginBase,
            )

    def test_wrong_superclass_raises(self):
        """A class not inheriting from super_cls must raise TypeError."""
        with self.assertRaises(TypeError):
            self.pm._create_class(
                'aprsd.plugins.ping.PingPlugin',
                super_cls=aprsd_plugin.APRSDWatchListPluginBase,
            )

    def test_valid_class_created(self):
        """A valid plugin fqn still instantiates."""
        obj = self.pm._create_class(
            'aprsd.plugins.ping.PingPlugin',
            super_cls=aprsd_plugin.APRSDPluginBase,
        )
        self.assertIsNotNone(obj)
        self.assertIsInstance(obj, aprsd_plugin.APRSDPluginBase)
