import unittest
from unittest import mock

from oslo_config import cfg

from aprsd import conf  # noqa: F401  - side-effect: registers oslo.config opts
from aprsd.threads import rx
from tests import fake

CONF = cfg.CONF


class TestAttachPiggybackAck(unittest.TestCase):
    """Unit tests for APRSDPluginProcessPacketThread._attach_piggyback_ack."""

    def setUp(self):
        """Set up test fixtures."""
        self.client_patcher = mock.patch('aprsd.threads.rx.APRSDClient')
        self.client_patcher.start()
        CONF.callsign = 'W1AW'

    def tearDown(self):
        """Clean up after tests."""
        self.client_patcher.stop()

    def test_attach_when_no_ackMsgNo_set(self):
        """The Reply-Ack is attached when no ackMsgNo is set."""
        response = fake.fake_packet(message='pong')

        with mock.patch.object(CONF, 'enable_piggyback_ack_packets', True):
            attached = rx.APRSDPluginProcessPacketThread._attach_piggyback_ack(
                None, response, '12'
            )

        self.assertTrue(attached)
        self.assertEqual(response.ackMsgNo, '12')

    def test_does_not_overwrite_plugin_set_ackMsgNo(self):
        """A plugin-set ackMsgNo is not overwritten."""
        response = fake.fake_packet(message='pong')
        response.ackMsgNo = '5'

        with mock.patch.object(CONF, 'enable_piggyback_ack_packets', True):
            attached = rx.APRSDPluginProcessPacketThread._attach_piggyback_ack(
                None, response, '12'
            )

        self.assertFalse(attached)
        self.assertEqual(response.ackMsgNo, '5')

    def test_not_attached_when_disabled(self):
        """No attachment when piggyback ack packets are disabled."""
        response = fake.fake_packet(message='pong')

        with mock.patch.object(CONF, 'enable_piggyback_ack_packets', False):
            attached = rx.APRSDPluginProcessPacketThread._attach_piggyback_ack(
                None, response, '12'
            )

        self.assertFalse(attached)
        self.assertIsNone(response.ackMsgNo)
