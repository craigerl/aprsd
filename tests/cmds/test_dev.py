import typing as t
import unittest
from unittest import mock

from click.testing import CliRunner
from oslo_config import cfg

from aprsd import conf  # noqa: F401
from aprsd.aprsd import cli
from aprsd.cmds import dev  # noqa

from .. import fake


CONF = cfg.CONF
F = t.TypeVar("F", bound=t.Callable[..., t.Any])


class TestDevTestPluginCommand(unittest.TestCase):

    def config_and_init(self, login=None, password=None):
        CONF.callsign = fake.FAKE_TO_CALLSIGN
        CONF.trace_enabled = False
        CONF.watch_list.packet_keep_count = 1
        if login:
            CONF.aprs_network.login = login
        if password:
            CONF.aprs_network.password = password

        CONF.admin.user = "admin"
        CONF.admin.password = "password"

    @mock.patch("aprsd.logging.log.setup_logging")
    def test_no_plugin_arg(self, mock_logging):
        """Make sure we get an error if there is no login and config."""

        runner = CliRunner()
        self.config_and_init(login="something")

        result = runner.invoke(
            cli, ["dev", "test-plugin", "bogus command"],
            catch_exceptions=False,
        )
        assert result.exit_code == 2
        assert "Failed to provide -p option to test a plugin" in result.output
