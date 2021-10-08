import abc
import logging
import time

import aprslib
from aprslib.exceptions import LoginError

from aprsd import trace
from aprsd.clients import aprsis, kiss


LOG = logging.getLogger("APRSD")
TRANSPORT_APRSIS = "aprsis"
TRANSPORT_TCPKISS = "tcpkiss"
TRANSPORT_SERIALKISS = "serialkiss"

# Main must create this from the ClientFactory
# object such that it's populated with the
# Correct config
factory = None


class Client:
    """Singleton client class that constructs the aprslib connection."""

    _instance = None
    _client = None
    config = None

    connected = False
    server_string = None

    def __new__(cls, *args, **kwargs):
        """This magic turns this into a singleton."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            # Put any initialization here.
        return cls._instance

    def __init__(self, config=None):
        """Initialize the object instance."""
        if config:
            self.config = config

    @property
    def client(self):
        if not self._client:
            self._client = self.setup_connection()
        return self._client

    def reset(self):
        """Call this to force a rebuild/reconnect."""
        del self._client

    @abc.abstractmethod
    def setup_connection(self):
        pass

    @staticmethod
    @abc.abstractmethod
    def is_enabled(config):
        pass

    @staticmethod
    @abc.abstractmethod
    def transport(config):
        pass

    @abc.abstractmethod
    def decode_packet(self, *args, **kwargs):
        pass


class APRSISClient(Client):

    @staticmethod
    def is_enabled(config):
        # Defaults to True if the enabled flag is non existent
        return config["aprs"].get("enabled", True)

    @staticmethod
    def transport(config):
        return TRANSPORT_APRSIS

    def decode_packet(self, *args, **kwargs):
        """APRS lib already decodes this."""
        return args[0]

    @trace.trace
    def setup_connection(self):
        user = self.config["aprs"]["login"]
        password = self.config["aprs"]["password"]
        host = self.config["aprs"].get("host", "rotate.aprs.net")
        port = self.config["aprs"].get("port", 14580)
        connected = False
        backoff = 1
        aprs_client = None
        while not connected:
            try:
                LOG.info("Creating aprslib client")
                aprs_client = aprsis.Aprsdis(user, passwd=password, host=host, port=port)
                # Force the logging to be the same
                aprs_client.logger = LOG
                aprs_client.connect()
                connected = True
                backoff = 1
            except LoginError as e:
                LOG.error(f"Failed to login to APRS-IS Server '{e}'")
                connected = False
                raise e
            except Exception as e:
                LOG.error(f"Unable to connect to APRS-IS server. '{e}' ")
                time.sleep(backoff)
                backoff = backoff * 2
                continue
        LOG.debug(f"Logging in to APRS-IS with user '{user}'")
        return aprs_client


class KISSClient(Client):

    @staticmethod
    def is_enabled(config):
        """Return if tcp or serial KISS is enabled."""
        if "kiss" not in config:
            return False

        if config.get("kiss.serial.enabled", default=False):
            return True

        if config.get("kiss.tcp.enabled", default=False):
            return True

    @staticmethod
    def transport(config):
        if config.get("kiss.serial.enabled", default=False):
            return TRANSPORT_SERIALKISS

        if config.get("kiss.tcp.enabled", default=False):
            return TRANSPORT_TCPKISS

    def decode_packet(self, *args, **kwargs):
        """We get a frame, which has to be decoded."""
        frame = kwargs["frame"]
        LOG.debug(f"Got an APRS Frame '{frame}'")
        # try and nuke the * from the fromcall sign.
        frame.header._source._ch = False
        payload = str(frame.payload.decode())
        msg = f"{str(frame.header)}:{payload}"
        # msg = frame.tnc2
        LOG.debug(f"Decoding {msg}")

        packet = aprslib.parse(msg)
        return packet

    @trace.trace
    def setup_connection(self):
        ax25client = kiss.Aioax25Client(self.config)
        return ax25client


class ClientFactory:
    _instance = None

    def __new__(cls, *args, **kwargs):
        """This magic turns this into a singleton."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            # Put any initialization here.
        return cls._instance

    def __init__(self, config):
        self.config = config
        self._builders = {}

    def register(self, key, builder):
        self._builders[key] = builder

    def create(self, key=None):
        if not key:
            if APRSISClient.is_enabled(self.config):
                key = TRANSPORT_APRSIS
            elif KISSClient.is_enabled(self.config):
                key = KISSClient.transport(self.config)

        LOG.debug(f"GET client {key}")
        builder = self._builders.get(key)
        if not builder:
            raise ValueError(key)
        return builder(self.config)

    def is_client_enabled(self):
        """Make sure at least one client is enabled."""
        enabled = False
        for key in self._builders.keys():
            enabled |= self._builders[key].is_enabled(self.config)

        return enabled

    @staticmethod
    def setup(config):
        """Create and register all possible client objects."""
        global factory

        factory = ClientFactory(config)
        factory.register(TRANSPORT_APRSIS, APRSISClient)
        factory.register(TRANSPORT_TCPKISS, KISSClient)
        factory.register(TRANSPORT_SERIALKISS, KISSClient)
