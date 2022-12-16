from unittest import mock

from aprsd import packets
from aprsd.packets import tracker
from aprsd.plugins import query as query_plugin

from .. import fake, test_plugin


class TestQueryPlugin(test_plugin.TestPlugin):
    @mock.patch("aprsd.packets.tracker.PacketTrack.flush")
    def test_query_flush(self, mock_flush):
        packet = fake.fake_packet(message="!delete")
        query = query_plugin.QueryPlugin(self.config)

        expected = "Deleted ALL pending msgs."
        actual = query.filter(packet)
        mock_flush.assert_called_once()
        self.assertEqual(expected, actual)

    @mock.patch("aprsd.packets.tracker.PacketTrack.restart_delayed")
    def test_query_restart_delayed(self, mock_restart):
        track = tracker.PacketTrack()
        track.data = {}
        packet = fake.fake_packet(message="!4")
        query = query_plugin.QueryPlugin(self.config)

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
