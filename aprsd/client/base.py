import abc
import logging
import threading

from oslo_config import cfg
import wrapt

from aprsd.packets import core


CONF = cfg.CONF
LOG = logging.getLogger("APRSD")


class APRSClient:
    """Singleton client class that constructs the aprslib connection."""

    _instance = None
    _client = None

    connected = False
    filter = None
    lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        """This magic turns this into a singleton."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            # Put any initialization here.
            cls._instance._create_client()
        return cls._instance

    @abc.abstractmethod
    def stats(self) -> dict:
        pass

    def set_filter(self, filter):
        self.filter = filter
        if self._client:
            self._client.set_filter(filter)

    @property
    def client(self):
        if not self._client:
            self._create_client()
        return self._client

    def _create_client(self):
        self._client = self.setup_connection()
        if self.filter:
            LOG.info("Creating APRS client filter")
            self._client.set_filter(self.filter)

    def stop(self):
        if self._client:
            LOG.info("Stopping client connection.")
            self._client.stop()

    def send(self, packet: core.Packet):
        """Send a packet to the network."""
        self.client.send(packet)

    @wrapt.synchronized(lock)
    def reset(self):
        """Call this to force a rebuild/reconnect."""
        LOG.info("Resetting client connection.")
        if self._client:
            self._client.close()
            del self._client
            self._create_client()
        else:
            LOG.warning("Client not initialized, nothing to reset.")

        # Recreate the client
        LOG.info(f"Creating new client {self.client}")

    @abc.abstractmethod
    def setup_connection(self):
        pass

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
        pass

    @abc.abstractmethod
    def consumer(self, callback, blocking=False, immortal=False, raw=False):
        pass

    @abc.abstractmethod
    def is_alive(self):
        pass

    @abc.abstractmethod
    def close(self):
        pass
