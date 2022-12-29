from unittest import mock

from oslo_config import cfg

from aprsd import packets
from aprsd.packets import tracker
from aprsd.plugins import query as query_plugin

from .. import fake, test_plugin


CONF = cfg.CONF


class TestQueryPlugin(test_plugin.TestPlugin):
    @mock.patch("aprsd.packets.tracker.PacketTrack.flush")
    def test_query_flush(self, mock_flush):
        packet = fake.fake_packet(message="!delete")
        CONF.callsign = fake.FAKE_TO_CALLSIGN
        CONF.save_enabled = True
        CONF.query_plugin.callsign = fake.FAKE_FROM_CALLSIGN
        query = query_plugin.QueryPlugin()
        query.enabled = True

        expected = "Deleted ALL pending msgs."
        actual = query.filter(packet)
        mock_flush.assert_called_once()
        self.assertEqual(expected, actual)

    @mock.patch("aprsd.packets.tracker.PacketTrack.restart_delayed")
    def test_query_restart_delayed(self, mock_restart):
        CONF.callsign = fake.FAKE_TO_CALLSIGN
        CONF.save_enabled = True
        CONF.query_plugin.callsign = fake.FAKE_FROM_CALLSIGN
        track = tracker.PacketTrack()
        track.data = {}
        packet = fake.fake_packet(message="!4")
        query = query_plugin.QueryPlugin()

        expected = "No pending msgs to resend"
        actual = query.filter(packet)
        mock_restart.assert_not_called()
        self.assertEqual(expected, actual)
        mock_restart.reset_mock()

        # add a message
        pkt = packets.MessagePacket(
            from_call=self.fromcall,
            to_call="testing",
            msgNo=self.ack,
        )
        track.add(pkt)
        actual = query.filter(packet)
        mock_restart.assert_called_once()
