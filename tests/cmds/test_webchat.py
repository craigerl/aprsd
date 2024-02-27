import typing as t
import unittest
from unittest import mock

from click.testing import CliRunner
import flask
import flask_socketio
from oslo_config import cfg

from aprsd import conf  # noqa: F401
from aprsd.cmds import webchat  # noqa
from aprsd.packets import core

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
    def test_init_flask(self, mock_logging):
        """Make sure we get an error if there is no login and config."""

        CliRunner()
        self.config_and_init()

        socketio = webchat.init_flask("DEBUG", False)
        self.assertIsInstance(socketio, flask_socketio.SocketIO)
        self.assertIsInstance(webchat.flask_app, flask.Flask)

    @mock.patch("aprsd.packets.tracker.PacketTrack.remove")
    @mock.patch("aprsd.cmds.webchat.socketio")
    def test_process_ack_packet(
        self,
        mock_remove, mock_socketio,
    ):
        self.config_and_init()
        mock_socketio.emit = mock.MagicMock()
        packet = fake.fake_packet(
            message="blah",
            msg_number=1,
            message_format=core.PACKET_TYPE_ACK,
        )
        mock_queue = mock.MagicMock()
        socketio = mock.MagicMock()
        wcp = webchat.WebChatProcessPacketThread(mock_queue, socketio)

        wcp.process_ack_packet(packet)
        mock_remove.called_once()
        mock_socketio.called_once()

    @mock.patch("aprsd.threads.tx.send")
    @mock.patch("aprsd.packets.PacketList.rx")
    @mock.patch("aprsd.cmds.webchat.socketio")
    def test_process_our_message_packet(
        self,
        mock_tx_send,
        mock_packet_add,
        mock_socketio,
    ):
        self.config_and_init()
        mock_socketio.emit = mock.MagicMock()
        packet = fake.fake_packet(
            message="blah",
            msg_number=1,
            message_format=core.PACKET_TYPE_MESSAGE,
        )
        mock_queue = mock.MagicMock()
        socketio = mock.MagicMock()
        wcp = webchat.WebChatProcessPacketThread(mock_queue, socketio)

        wcp.process_our_message_packet(packet)
        mock_packet_add.called_once()
        mock_socketio.called_once()
