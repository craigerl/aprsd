from unittest import mock

from aprsd.packets import core


class MockClientDriver:
    """Mock implementation of ClientDriver for testing."""

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

    @staticmethod
    def is_enabled():
        """Static method to check if driver is enabled."""
        return True

    @staticmethod
    def is_configured():
        """Static method to check if driver is configured."""
        return True

    def is_alive(self):
        """Instance method to check if driver is alive."""
        return self._alive

    def stats(self, serializable=False):
        """Return mock stats."""
        stats = {'packets_received': 0, 'packets_sent': 0}
        if serializable:
            stats['path'] = self.path
        return stats

    @property
    def login_success(self):
        """Property to get login success status."""
        return self.login_status['success']

    @property
    def login_failure(self):
        """Property to get login failure message."""
        return self.login_status['message']

    def decode_packet(self, *args, **kwargs):
        """Mock packet decoding."""
        packet = mock.MagicMock(spec=core.Packet)
        packet.raw = 'test packet'
        return packet

    def close(self):
        self.connected = False

    def setup_connection(self):
        self.connected = True

    def send(self, packet):
        return True

    def set_filter(self, filter_str):
        self.filter = filter_str

    @property
    def keepalive(self):
        return self._keepalive

    def consumer(self, callback, raw=False):
        pass
