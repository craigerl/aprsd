import unittest
from unittest import mock

from aprsd.client.drivers.fake import APRSDFakeDriver
from aprsd.packets import core


class TestAPRSDFakeDriver(unittest.TestCase):
    """Unit tests for the APRSDFakeDriver class."""

    def setUp(self):
        # Mock CONF for testing
        self.conf_patcher = mock.patch('aprsd.client.drivers.fake.CONF')
        self.mock_conf = self.conf_patcher.start()

        # Configure fake_client.enabled
        self.mock_conf.fake_client.enabled = True

        # Create an instance of the driver
        self.driver = APRSDFakeDriver()

    def tearDown(self):
        self.conf_patcher.stop()

    def test_init(self):
        """Test initialization sets default values."""
        self.assertEqual(self.driver.path, ['WIDE1-1', 'WIDE2-1'])
        self.assertFalse(self.driver.thread_stop)

    def test_is_enabled_true(self):
        """Test is_enabled returns True when configured."""
        self.mock_conf.fake_client.enabled = True
        self.assertTrue(APRSDFakeDriver.is_enabled())

    def test_is_enabled_false(self):
        """Test is_enabled returns False when not configured."""
        self.mock_conf.fake_client.enabled = False
        self.assertFalse(APRSDFakeDriver.is_enabled())

    def test_is_alive(self):
        """Test is_alive returns True when thread_stop is False."""
        self.driver.thread_stop = False
        self.assertTrue(self.driver.is_alive())

        self.driver.thread_stop = True
        self.assertFalse(self.driver.is_alive())

    def test_close(self):
        """Test close sets thread_stop to True."""
        self.driver.thread_stop = False
        self.driver.close()
        self.assertTrue(self.driver.thread_stop)

    @mock.patch('aprsd.client.drivers.fake.LOG')
    def test_setup_connection(self, mock_log):
        """Test setup_connection does nothing (it's fake)."""
        self.driver.setup_connection()
        # Method doesn't do anything, so just verify it doesn't crash

    def test_set_filter(self):
        """Test set_filter method does nothing (it's fake)."""
        # Just test it doesn't fail
        self.driver.set_filter('test/filter')

    def test_login_success(self):
        """Test login_success always returns True."""
        self.assertTrue(self.driver.login_success())

    def test_login_failure(self):
        """Test login_failure always returns None."""
        self.assertIsNone(self.driver.login_failure())

    @mock.patch('aprsd.client.drivers.fake.LOG')
    def test_send_with_packet_object(self, mock_log):
        """Test send with a Packet object."""
        mock_packet = mock.MagicMock(spec=core.Packet)
        mock_packet.payload = 'Test payload'
        mock_packet.to_call = 'TEST'
        mock_packet.from_call = 'FAKE'

        self.driver.send(mock_packet)

        mock_log.info.assert_called_once()
        mock_packet.prepare.assert_called_once()

    @mock.patch('aprsd.client.drivers.fake.LOG')
    def test_send_with_non_packet_object(self, mock_log):
        """Test send with a non-Packet object."""
        # Create a mock message-like object
        mock_msg = mock.MagicMock()
        mock_msg.raw = 'Test'
        mock_msg.msgNo = '123'
        mock_msg.to_call = 'TEST'
        mock_msg.from_call = 'FAKE'

        self.driver.send(mock_msg)

        mock_log.info.assert_called_once()
        mock_log.debug.assert_called_once()

    @mock.patch('aprsd.client.drivers.fake.LOG')
    @mock.patch('aprsd.client.drivers.fake.time.sleep')
    def test_consumer_with_raw_true(self, mock_sleep, mock_log):
        """Test consumer with raw=True."""
        mock_callback = mock.MagicMock()

        self.driver.consumer(mock_callback, raw=True)

        # Verify callback was called with raw data
        mock_callback.assert_called_once()
        call_args = mock_callback.call_args[1]
        self.assertIn('raw', call_args)
        mock_sleep.assert_called_once_with(1)

    @mock.patch('aprsd.client.drivers.fake.LOG')
    @mock.patch('aprsd.client.drivers.fake.aprslib.parse')
    @mock.patch('aprsd.client.drivers.fake.core.factory')
    @mock.patch('aprsd.client.drivers.fake.time.sleep')
    def test_consumer_with_raw_false(
        self, mock_sleep, mock_factory, mock_parse, mock_log
    ):
        """Test consumer with raw=False."""
        mock_callback = mock.MagicMock()
        mock_packet = mock.MagicMock(spec=core.Packet)
        mock_factory.return_value = mock_packet

        self.driver.consumer(mock_callback, raw=False)

        # Verify the packet was created and passed to callback
        mock_parse.assert_called_once()
        mock_factory.assert_called_once()
        mock_callback.assert_called_once_with(packet=mock_packet)
        mock_sleep.assert_called_once_with(1)

    def test_consumer_updates_keepalive(self):
        """Test consumer updates keepalive timestamp."""
        mock_callback = mock.MagicMock()
        old_keepalive = self.driver.aprsd_keepalive

        # Force a small delay to ensure timestamp changes
        import time

        time.sleep(0.01)

        with mock.patch('aprsd.client.drivers.fake.time.sleep'):
            self.driver.consumer(mock_callback)

        self.assertNotEqual(old_keepalive, self.driver.aprsd_keepalive)
        self.assertGreater(self.driver.aprsd_keepalive, old_keepalive)

    def test_decode_packet_with_empty_kwargs(self):
        """Test decode_packet with empty kwargs."""
        result = self.driver.decode_packet()
        self.assertIsNone(result)

    def test_decode_packet_with_packet(self):
        """Test decode_packet with packet in kwargs."""
        mock_packet = mock.MagicMock(spec=core.Packet)
        result = self.driver.decode_packet(packet=mock_packet)
        self.assertEqual(result, mock_packet)

    @mock.patch('aprsd.client.drivers.fake.aprslib.parse')
    @mock.patch('aprsd.client.drivers.fake.core.factory')
    def test_decode_packet_with_raw(self, mock_factory, mock_parse):
        """Test decode_packet with raw in kwargs."""
        mock_packet = mock.MagicMock(spec=core.Packet)
        mock_factory.return_value = mock_packet
        raw_data = 'raw packet data'

        result = self.driver.decode_packet(raw=raw_data)

        mock_parse.assert_called_once_with(raw_data)
        mock_factory.assert_called_once_with(mock_parse.return_value)
        self.assertEqual(result, mock_packet)

    def test_stats(self):
        """Test stats returns correct information."""
        self.driver.thread_stop = False
        result = self.driver.stats()

        self.assertEqual(result['driver'], 'APRSDFakeDriver')
        self.assertTrue(result['is_alive'])

        # Test with serializable parameter
        result_serializable = self.driver.stats(serializable=True)
        self.assertEqual(result_serializable['driver'], 'APRSDFakeDriver')
        self.assertTrue(result_serializable['is_alive'])


if __name__ == '__main__':
    unittest.main()
