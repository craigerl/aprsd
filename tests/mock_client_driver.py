from unittest import mock

from aprsd.packets import core


class MockClientDriver:
    """Mock implementation of ClientDriver for testing.

    This class can be used both as a class (for registration) and as an instance.
    When used as a class, it implements the ClientDriver Protocol.
    When instantiated, it returns a mock driver instance.
    """

    _instance = None

    def __init__(self, enabled=True, configured=True):
        self.connected = False
        self._alive = True
        self._keepalive = None
        self.filter = None
        self._enabled = enabled
        self._configured = configured
        self.path = '/dev/ttyUSB0'
        self.login_status = {
            'success': True,
            'message': None,
        }
        # Make methods mockable
        self.close = mock.MagicMock(side_effect=self._close)
        self.setup_connection = mock.MagicMock(side_effect=self._setup_connection)
        self.send = mock.MagicMock(side_effect=self._send)
        self.set_filter = mock.MagicMock(side_effect=self._set_filter)
        self.consumer = mock.MagicMock(side_effect=self._consumer)
        self.decode_packet = mock.MagicMock(side_effect=self._decode_packet)

    @staticmethod
    def is_enabled():
        """Static method to check if driver is enabled."""
        return True

    @staticmethod
    def is_configured():
        """Static method to check if driver is configured."""
        return True

    def __call__(self):
        """Make the class callable to return an instance (singleton pattern)."""
        if self._instance is None:
            self._instance = self
        return self._instance

    @property
    def is_alive(self):
        """Property to check if driver is alive."""
        return self._alive

    def stats(self, serializable=False):
        """Return mock stats."""
        stats = {'packets_received': 0, 'packets_sent': 0}
        if serializable:
            stats['path'] = self.path
        return stats

    def login_success(self):
        """Method to get login success status."""
        return self.login_status['success']

    def login_failure(self):
        """Method to get login failure message."""
        return self.login_status['message']

    def _decode_packet(self, *args, **kwargs):
        """Mock packet decoding."""
        if hasattr(self, '_decode_packet_return'):
            return self._decode_packet_return
        packet = mock.MagicMock(spec=core.Packet)
        packet.raw = 'test packet'
        packet.path = []
        packet.human_info = 'test packet info'
        return packet

    def _close(self):
        self.connected = False

    def _setup_connection(self):
        self.connected = True
        self._alive = True  # Make driver alive after connection

    def _send(self, packet):
        if hasattr(self, '_send_side_effect'):
            if isinstance(self._send_side_effect, Exception):
                raise self._send_side_effect
        if hasattr(self, '_send_return'):
            return self._send_return
        return True

    def _set_filter(self, filter_str):
        self.filter = filter_str

    @property
    def keepalive(self):
        return self._keepalive

    def _consumer(self, callback, raw=False):
        if hasattr(self, '_consumer_side_effect'):
            if isinstance(self._consumer_side_effect, Exception):
                raise self._consumer_side_effect
        if hasattr(self, '_consumer_callback'):
            self._consumer_callback(callback)
        elif callback:
            callback()

    def reset(self):
        """Reset the driver connection."""
        self.connected = False
        self._alive = False
