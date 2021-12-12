import typing as t
import unittest
from unittest import mock

from click.testing import CliRunner

from aprsd import config as aprsd_config
from aprsd.aprsd import cli
from aprsd.cmds import dev  # noqa


F = t.TypeVar("F", bound=t.Callable[..., t.Any])


class TestDevTestPluginCommand(unittest.TestCase):

    def _build_config(self, login=None, password=None):
        config = {"aprs": {}}
        if login:
            config["aprs"]["login"] = login

        if password:
            config["aprs"]["password"] = password

        return aprsd_config.Config(config)

    @mock.patch("aprsd.config.parse_config")
    @mock.patch("aprsd.log.setup_logging")
    def test_no_login(self, mock_logging, mock_parse_config):
        """Make sure we get an error if there is no login and config."""

        runner = CliRunner()
        mock_parse_config.return_value = self._build_config()

        result = runner.invoke(
            cli, ["dev", "test-plugin", "bogus command"],
            catch_exceptions=False,
        )
        # rich.print(f"EXIT CODE {result.exit_code}")
        # rich.print(f"Exception {result.exception}")
        # rich.print(f"OUTPUT {result.output}")
        assert result.exit_code == -1
        assert "Must set --aprs_login or APRS_LOGIN" in result.output

    @mock.patch("aprsd.config.parse_config")
    @mock.patch("aprsd.log.setup_logging")
    def test_no_plugin_arg(self, mock_logging, mock_parse_config):
        """Make sure we get an error if there is no login and config."""

        runner = CliRunner()
        mock_parse_config.return_value = self._build_config(login="something")

        result = runner.invoke(
            cli, ["dev", "test-plugin", "bogus command"],
            catch_exceptions=False,
        )
        assert result.exit_code == 2
        assert "Failed to provide -p option to test a plugin" in result.output
