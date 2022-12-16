import typing as t
import unittest
from unittest import mock

from click.testing import CliRunner
import flask
import flask_socketio

from aprsd import config as aprsd_config
from aprsd import packets
from aprsd.cmds import webchat  # noqa
from aprsd.packets import core

from .. import fake


F = t.TypeVar("F", bound=t.Callable[..., t.Any])


class TestSendMessageCommand(unittest.TestCase):

    def _build_config(self, login=None, password=None):
        config = {
            "aprs": {},
            "aprsd": {
                "trace": False,
                "web": {
                    "users": {"admin": "password"},
                },
                "watch_list": {"packet_keep_count": 1},
            },
        }
        if login:
            config["aprs"]["login"] = login

        if password:
            config["aprs"]["password"] = password

        return aprsd_config.Config(config)

    @mock.patch("aprsd.config.parse_config")
    def test_missing_config(self, mock_parse_config):
        CliRunner()
        cfg = self._build_config()
        del cfg["aprsd"]["web"]["users"]
        mock_parse_config.return_value = cfg

        server = webchat.WebChatFlask()
        self.assertRaises(
            KeyError,
            server.set_config, cfg,
        )

    @mock.patch("aprsd.config.parse_config")
    @mock.patch("aprsd.logging.log.setup_logging")
    def test_init_flask(self, mock_logging, mock_parse_config):
        """Make sure we get an error if there is no login and config."""

        CliRunner()
        cfg = self._build_config()
        mock_parse_config.return_value = cfg

        socketio, flask_app = webchat.init_flask(cfg, "DEBUG", False)
        self.assertIsInstance(socketio, flask_socketio.SocketIO)
        self.assertIsInstance(flask_app, flask.Flask)

    @mock.patch("aprsd.config.parse_config")
    @mock.patch("aprsd.packets.tracker.PacketTrack.remove")
    @mock.patch("aprsd.cmds.webchat.socketio.emit")
    def test_process_ack_packet(
        self, mock_parse_config,
        mock_remove, mock_emit,
    ):
        config = self._build_config()
        mock_parse_config.return_value = config
        packet = fake.fake_packet(
            message="blah",
            msg_number=1,
            message_format=core.PACKET_TYPE_ACK,
        )
        socketio = mock.MagicMock()
        packets.PacketList(config=config)
        packets.PacketTrack(config=config)
        packets.WatchList(config=config)
        packets.SeenList(config=config)
        wcp = webchat.WebChatProcessPacketThread(config, packet, socketio)

        wcp.process_ack_packet(packet)
        mock_remove.called_once()
        mock_emit.called_once()

    @mock.patch("aprsd.config.parse_config")
    @mock.patch("aprsd.packets.PacketList.add")
    @mock.patch("aprsd.cmds.webchat.socketio.emit")
    def test_process_our_message_packet(
        self, mock_parse_config,
        mock_packet_add,
        mock_emit,
    ):
        config = self._build_config()
        mock_parse_config.return_value = config
        packet = fake.fake_packet(
            message="blah",
            msg_number=1,
            message_format=core.PACKET_TYPE_MESSAGE,
        )
        socketio = mock.MagicMock()
        packets.PacketList(config=config)
        packets.PacketTrack(config=config)
        packets.WatchList(config=config)
        packets.SeenList(config=config)
        wcp = webchat.WebChatProcessPacketThread(config, packet, socketio)

        wcp.process_our_message_packet(packet)
        mock_packet_add.called_once()
        mock_emit.called_once()
