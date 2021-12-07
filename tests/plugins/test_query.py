from unittest import mock

from aprsd import messaging
from aprsd.plugins import query as query_plugin

from .. import fake, test_plugin


class TestQueryPlugin(test_plugin.TestPlugin):
    @mock.patch("aprsd.messaging.MsgTrack.flush")
    def test_query_flush(self, mock_flush):
        packet = fake.fake_packet(message="!delete")
        query = query_plugin.QueryPlugin(self.config)

        expected = "Deleted ALL pending msgs."
        actual = query.filter(packet)
        mock_flush.assert_called_once()
        self.assertEqual(expected, actual)

    @mock.patch("aprsd.messaging.MsgTrack.restart_delayed")
    def test_query_restart_delayed(self, mock_restart):
        track = messaging.MsgTrack()
        track.data = {}
        packet = fake.fake_packet(message="!4")
        query = query_plugin.QueryPlugin(self.config)

        expected = "No pending msgs to resend"
        actual = query.filter(packet)
        mock_restart.assert_not_called()
        self.assertEqual(expected, actual)
        mock_restart.reset_mock()

        # add a message
        msg = messaging.TextMessage(self.fromcall, "testing", self.ack)
        track.add(msg)
        actual = query.filter(packet)
        mock_restart.assert_called_once()
