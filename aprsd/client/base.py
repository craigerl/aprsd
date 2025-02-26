import abc
import logging
import threading

import wrapt
from oslo_config import cfg

from aprsd.packets import core
from aprsd.utils import keepalive_collector

CONF = cfg.CONF
LOG = logging.getLogger('APRSD')


class APRSClient:
    """Singleton client class that constructs the aprslib connection."""

    _instance = None
    _client = None

    connected = False
    login_status = {
        'success': False,
        'message': None,
    }
    filter = None
    lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        """This magic turns this into a singleton."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            keepalive_collector.KeepAliveCollector().register(cls)
            # Put any initialization here.
            cls._instance._create_client()
        return cls._instance

    @abc.abstractmethod
    def stats(self) -> dict:
        """Return statistics about the client connection.

        Returns:
            dict: Statistics about the connection and packet handling
        """

    @abc.abstractmethod
    def keepalive_check(self) -> None:
        """Called during keepalive run to check status."""
        ...

    @abc.abstractmethod
    def keepalive_log(self) -> None:
        """Log any keepalive information."""
        ...

    @property
    def is_connected(self):
        return self.connected

    @property
    def login_success(self):
        return self.login_status.get('success', False)

    @property
    def login_failure(self):
        return self.login_status['message']

    def set_filter(self, filter):
        self.filter = filter
        if self._client:
            self._client.set_filter(filter)

    def get_filter(self):
        return self.filter

    @property
    def client(self):
        if not self._client:
            self._create_client()
        return self._client

    def _create_client(self):
        try:
            self._client = self.setup_connection()
            if self.filter:
                LOG.info('Creating APRS client filter')
                self._client.set_filter(self.filter)
        except Exception as e:
            LOG.error(f'Failed to create APRS client: {e}')
            self._client = None
            raise

    def stop(self):
        if self._client:
            LOG.info('Stopping client connection.')
            self._client.stop()

    def send(self, packet: core.Packet) -> None:
        """Send a packet to the network.

        Args:
            packet: The APRS packet to send
        """
        self.client.send(packet)

    @wrapt.synchronized(lock)
    def reset(self) -> None:
        """Call this to force a rebuild/reconnect."""
        LOG.info('Resetting client connection.')
        if self._client:
            self._client.close()
            del self._client
            self._create_client()
        else:
            LOG.warning('Client not initialized, nothing to reset.')

        # Recreate the client
        LOG.info(f'Creating new client {self.client}')

    @abc.abstractmethod
    def setup_connection(self):
        """Initialize and return the underlying APRS connection.

        Returns:
            object: The initialized connection object
        """

    @staticmethod
    @abc.abstractmethod
    def is_enabled():
        pass

    @staticmethod
    @abc.abstractmethod
    def transport():
        pass

    @abc.abstractmethod
    def decode_packet(self, *args, **kwargs):
        """Decode raw APRS packet data into a Packet object.

        Returns:
            Packet: Decoded APRS packet
        """

    @abc.abstractmethod
    def consumer(self, callback, blocking=False, immortal=False, raw=False):
        pass

    @abc.abstractmethod
    def is_alive(self):
        pass

    @abc.abstractmethod
    def close(self):
        pass
