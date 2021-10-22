import datetime
import unittest
from unittest import mock

from aprsd import messaging


class TestMessageTrack(unittest.TestCase):

    def setUp(self) -> None:
        config = {}
        messaging.MsgTrack(config=config)

    def _clean_track(self):
        track = messaging.MsgTrack()
        track.data = {}
        track.total_messages_tracked = 0
        return track

    def test_create(self):
        track1 = messaging.MsgTrack()
        track2 = messaging.MsgTrack()

        self.assertEqual(track1, track2)

    def test_add(self):
        track = self._clean_track()
        fromcall = "KFART"
        tocall = "KHELP"
        message = "somthing"
        msg = messaging.TextMessage(fromcall, tocall, message)

        track.add(msg)
        self.assertEqual(msg, track.get(msg.id))

    def test_remove(self):
        track = self._clean_track()
        fromcall = "KFART"
        tocall = "KHELP"
        message = "somthing"
        msg = messaging.TextMessage(fromcall, tocall, message)
        track.add(msg)

        track.remove(msg.id)
        self.assertEqual(None, track.get(msg.id))

    def test_len(self):
        """Test getting length of tracked messages."""
        track = self._clean_track()
        fromcall = "KFART"
        tocall = "KHELP"
        message = "somthing"
        msg = messaging.TextMessage(fromcall, tocall, message)
        track.add(msg)
        self.assertEqual(1, len(track))
        msg2 = messaging.TextMessage(tocall, fromcall, message)
        track.add(msg2)
        self.assertEqual(2, len(track))

        track.remove(msg.id)
        self.assertEqual(1, len(track))

    @mock.patch("aprsd.messaging.TextMessage.send")
    def test__resend(self, mock_send):
        """Test the _resend method."""
        track = self._clean_track()
        fromcall = "KFART"
        tocall = "KHELP"
        message = "somthing"
        msg = messaging.TextMessage(fromcall, tocall, message)
        msg.last_send_attempt = 3
        track.add(msg)

        track._resend(msg)
        msg.send.assert_called_with()
        self.assertEqual(0, msg.last_send_attempt)

    @mock.patch("aprsd.messaging.TextMessage.send")
    def test_restart_delayed(self, mock_send):
        """Test the _resend method."""
        track = self._clean_track()
        fromcall = "KFART"
        tocall = "KHELP"
        message1 = "something"
        message2 = "something another"
        message3 = "something another again"

        mock1_send = mock.MagicMock()
        mock2_send = mock.MagicMock()
        mock3_send = mock.MagicMock()

        msg1 = messaging.TextMessage(fromcall, tocall, message1)
        msg1.last_send_attempt = 3
        msg1.last_send_time = datetime.datetime.now()
        msg1.send = mock1_send
        track.add(msg1)

        msg2 = messaging.TextMessage(tocall, fromcall, message2)
        msg2.last_send_attempt = 3
        msg2.last_send_time = datetime.datetime.now()
        msg2.send = mock2_send
        track.add(msg2)

        track.restart_delayed(count=None)
        msg1.send.assert_called_once()
        self.assertEqual(0, msg1.last_send_attempt)
        msg2.send.assert_called_once()
        self.assertEqual(0, msg2.last_send_attempt)

        msg1.last_send_attempt = 3
        msg1.send.reset_mock()
        msg2.last_send_attempt = 3
        msg2.send.reset_mock()

        track.restart_delayed(count=1)
        msg1.send.assert_not_called()
        msg2.send.assert_called_once()
        self.assertEqual(3, msg1.last_send_attempt)
        self.assertEqual(0, msg2.last_send_attempt)

        msg3 = messaging.TextMessage(tocall, fromcall, message3)
        msg3.last_send_attempt = 3
        msg3.last_send_time = datetime.datetime.now()
        msg3.send = mock3_send
        track.add(msg3)

        msg1.last_send_attempt = 3
        msg1.send.reset_mock()
        msg2.last_send_attempt = 3
        msg2.send.reset_mock()
        msg3.last_send_attempt = 3
        msg3.send.reset_mock()

        track.restart_delayed(count=2)
        msg1.send.assert_not_called()
        msg2.send.assert_called_once()
        msg3.send.assert_called_once()
        self.assertEqual(3, msg1.last_send_attempt)
        self.assertEqual(0, msg2.last_send_attempt)
        self.assertEqual(0, msg3.last_send_attempt)

        msg1.last_send_attempt = 3
        msg1.send.reset_mock()
        msg2.last_send_attempt = 3
        msg2.send.reset_mock()
        msg3.last_send_attempt = 3
        msg3.send.reset_mock()

        track.restart_delayed(count=2, most_recent=False)
        msg1.send.assert_called_once()
        msg2.send.assert_called_once()
        msg3.send.assert_not_called()
        self.assertEqual(0, msg1.last_send_attempt)
        self.assertEqual(0, msg2.last_send_attempt)
        self.assertEqual(3, msg3.last_send_attempt)
