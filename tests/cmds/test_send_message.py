import typing as t
import unittest
from unittest import mock

from click.testing import CliRunner

from aprsd import config as aprsd_config
from aprsd.aprsd import cli
from aprsd.cmds import send_message  # noqa


F = t.TypeVar("F", bound=t.Callable[..., t.Any])


class TestSendMessageCommand(unittest.TestCase):

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
            cli, ["send-message", "WB4BOR", "wx"],
            catch_exceptions=False,
        )
        # rich.print(f"EXIT CODE {result.exit_code}")
        # rich.print(f"Exception {result.exception}")
        # rich.print(f"OUTPUT {result.output}")
        assert result.exit_code == -1
        assert "Must set --aprs_login or APRS_LOGIN" in result.output

    @mock.patch("aprsd.config.parse_config")
    @mock.patch("aprsd.log.setup_logging")
    def test_no_password(self, mock_logging, mock_parse_config):
        """Make sure we get an error if there is no password and config."""

        runner = CliRunner()
        mock_parse_config.return_value = self._build_config(login="something")

        result = runner.invoke(
            cli, ["send-message", "WB4BOR", "wx"],
            catch_exceptions=False,
        )
        assert result.exit_code == -1
        assert "Must set --aprs-password or APRS_PASSWORD" in result.output

    @mock.patch("aprsd.config.parse_config")
    @mock.patch("aprsd.log.setup_logging")
    def test_no_tocallsign(self, mock_logging, mock_parse_config):
        """Make sure we get an error if there is no tocallsign."""

        runner = CliRunner()
        mock_parse_config.return_value = self._build_config(
            login="something",
            password="another",
        )

        result = runner.invoke(
            cli, ["send-message"],
            catch_exceptions=False,
        )
        assert result.exit_code == 2
        assert "Error: Missing argument 'TOCALLSIGN'" in result.output

    @mock.patch("aprsd.config.parse_config")
    @mock.patch("aprsd.log.setup_logging")
    def test_no_command(self, mock_logging, mock_parse_config):
        """Make sure we get an error if there is no command."""

        runner = CliRunner()
        mock_parse_config.return_value = self._build_config(
            login="something",
            password="another",
        )

        result = runner.invoke(
            cli, ["send-message", "WB4BOR"],
            catch_exceptions=False,
        )
        assert result.exit_code == 2
        assert "Error: Missing argument 'COMMAND...'" in result.output
