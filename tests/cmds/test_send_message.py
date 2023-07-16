import typing as t
import unittest
from unittest import mock

from click.testing import CliRunner
from oslo_config import cfg

from aprsd import conf  # noqa : F401
from aprsd.cmds import send_message  # noqa
from aprsd.main import cli

from .. import fake


CONF = cfg.CONF
F = t.TypeVar("F", bound=t.Callable[..., t.Any])


class TestSendMessageCommand(unittest.TestCase):

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

    @mock.patch("aprsd.log.log.setup_logging")
    def test_no_tocallsign(self, mock_logging):
        """Make sure we get an error if there is no tocallsign."""

        self.config_and_init(
            login="something",
            password="another",
        )
        runner = CliRunner()

        result = runner.invoke(
            cli, ["send-message"],
            catch_exceptions=False,
        )
        assert result.exit_code == 2
        assert "Error: Missing argument 'TOCALLSIGN'" in result.output

    @mock.patch("aprsd.log.log.setup_logging")
    def test_no_command(self, mock_logging):
        """Make sure we get an error if there is no command."""

        self.config_and_init(
            login="something",
            password="another",
        )
        runner = CliRunner()

        result = runner.invoke(
            cli, ["send-message", "WB4BOR"],
            catch_exceptions=False,
        )
        assert result.exit_code == 2
        assert "Error: Missing argument 'COMMAND...'" in result.output
