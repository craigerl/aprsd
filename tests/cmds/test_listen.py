import unittest
from unittest import mock

from click.testing import CliRunner
from oslo_config import cfg

from aprsd.cmds import listen  # noqa: F401
from aprsd.main import cli

CONF = cfg.CONF


class TestListenCommand(unittest.TestCase):
    def test_loads_saved_stores_before_starting(self):
        """listen must load the stores it will save back on exit."""
        runner = CliRunner()
        with (
            mock.patch('aprsd.cmds.listen.packet_collector') as packet_collector,
            mock.patch('aprsd.cmds.listen.APRSDClient') as client_cls,
            mock.patch('aprsd.cmds.listen.keepalive.KeepAliveThread'),
            mock.patch('aprsd.cmds.listen.rx.APRSDRXThread'),
            mock.patch('aprsd.cmds.listen.APRSDListenProcessThread'),
            mock.patch('aprsd.cmds.listen.stats_thread.APRSDStatsStoreThread'),
            mock.patch('aprsd.cmds.listen.PacketFilter'),
            mock.patch('aprsd.utils.package.log_installed_extensions_and_plugins'),
            mock.patch('aprsd.log.log.setup_logging'),
        ):
            client_cls.return_value.login_success.return_value = True
            result = runner.invoke(
                cli,
                ['listen', '--aprs-login', 'N0CALL', '--aprs-password', 'x', 'b/X'],
                catch_exceptions=False,
            )

        self.assertEqual(result.exit_code, 0, result.output)
        packet_collector.PacketCollector.return_value.load.assert_called_once()
