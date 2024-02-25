import abc
import logging
import time

import aprslib
from aprslib.exceptions import LoginError
from oslo_config import cfg

from aprsd import exception
from aprsd.clients import aprsis, fake, kiss
from aprsd.packets import core, packet_list
from aprsd.utils import trace


CONF = cfg.CONF
LOG = logging.getLogger("APRSD")
TRANSPORT_APRSIS = "aprsis"
TRANSPORT_TCPKISS = "tcpkiss"
TRANSPORT_SERIALKISS = "serialkiss"
TRANSPORT_FAKE = "fake"

# Main must create this from the ClientFactory
# object such that it's populated with the
# Correct config
factory = None


class Client:
    """Singleton client class that constructs the aprslib connection."""

    _instance = None
    _client = None

    connected = False
    server_string = None
    filter = None

    def __new__(cls, *args, **kwargs):
        """This magic turns this into a singleton."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            # Put any initialization here.
        return cls._instance

    def set_filter(self, filter):
        self.filter = filter
        if self._client:
            self._client.set_filter(filter)

    @property
    def client(self):
        if not self._client:
            LOG.info("Creating APRS client")
            self._client = self.setup_connection()
            if self.filter:
                LOG.info("Creating APRS client filter")
                self._client.set_filter(self.filter)
        return self._client

    def send(self, packet: core.Packet):
        packet_list.PacketList().tx(packet)
        self.client.send(packet)

    def reset(self):
        """Call this to force a rebuild/reconnect."""
        if self._client:
            del self._client
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


class APRSISClient(Client):

    _client = None

    @staticmethod
    def is_enabled():
        # Defaults to True if the enabled flag is non existent
        try:
            return CONF.aprs_network.enabled
        except KeyError:
            return False

    @staticmethod
    def is_configured():
        if APRSISClient.is_enabled():
            # Ensure that the config vars are correctly set
            if not CONF.aprs_network.login:
                LOG.error("Config aprs_network.login not set.")
                raise exception.MissingConfigOptionException(
                    "aprs_network.login is not set.",
                )
            if not CONF.aprs_network.password:
                LOG.error("Config aprs_network.password not set.")
                raise exception.MissingConfigOptionException(
                    "aprs_network.password is not set.",
                )
            if not CONF.aprs_network.host:
                LOG.error("Config aprs_network.host not set.")
                raise exception.MissingConfigOptionException(
                    "aprs_network.host is not set.",
                )

            return True
        return True

    def is_alive(self):
        if self._client:
            return self._client.is_alive()
        else:
            return False

    @staticmethod
    def transport():
        return TRANSPORT_APRSIS

    def decode_packet(self, *args, **kwargs):
        """APRS lib already decodes this."""
        return core.Packet.factory(args[0])

    def setup_connection(self):
        user = CONF.aprs_network.login
        password = CONF.aprs_network.password
        host = CONF.aprs_network.host
        port = CONF.aprs_network.port
        connected = False
        backoff = 1
        aprs_client = None
        while not connected:
            try:
                LOG.info("Creating aprslib client")
                aprs_client = aprsis.Aprsdis(user, passwd=password, host=host, port=port)
                # Force the log to be the same
                aprs_client.logger = LOG
                aprs_client.connect()
                connected = True
                backoff = 1
            except LoginError as e:
                LOG.error(f"Failed to login to APRS-IS Server '{e}'")
                connected = False
                time.sleep(backoff)
            except Exception as e:
                LOG.error(f"Unable to connect to APRS-IS server. '{e}' ")
                connected = False
                time.sleep(backoff)
                # Don't allow the backoff to go to inifinity.
                if backoff > 5:
                    backoff = 5
                else:
                    backoff += 1
                continue
        LOG.debug(f"Logging in to APRS-IS with user '{user}'")
        self._client = aprs_client
        return aprs_client


class KISSClient(Client):

    _client = None

    @staticmethod
    def is_enabled():
        """Return if tcp or serial KISS is enabled."""
        if CONF.kiss_serial.enabled:
            return True

        if CONF.kiss_tcp.enabled:
            return True

        return False

    @staticmethod
    def is_configured():
        # Ensure that the config vars are correctly set
        if KISSClient.is_enabled():
            transport = KISSClient.transport()
            if transport == TRANSPORT_SERIALKISS:
                if not CONF.kiss_serial.device:
                    LOG.error("KISS serial enabled, but no device is set.")
                    raise exception.MissingConfigOptionException(
                        "kiss_serial.device is not set.",
                    )
            elif transport == TRANSPORT_TCPKISS:
                if not CONF.kiss_tcp.host:
                    LOG.error("KISS TCP enabled, but no host is set.")
                    raise exception.MissingConfigOptionException(
                        "kiss_tcp.host is not set.",
                    )

            return True
        return False

    def is_alive(self):
        if self._client:
            return self._client.is_alive()
        else:
            return False

    @staticmethod
    def transport():
        if CONF.kiss_serial.enabled:
            return TRANSPORT_SERIALKISS

        if CONF.kiss_tcp.enabled:
            return TRANSPORT_TCPKISS

    def decode_packet(self, *args, **kwargs):
        """We get a frame, which has to be decoded."""
        LOG.debug(f"kwargs {kwargs}")
        frame = kwargs["frame"]
        LOG.debug(f"Got an APRS Frame '{frame}'")
        # try and nuke the * from the fromcall sign.
        # frame.header._source._ch = False
        # payload = str(frame.payload.decode())
        # msg = f"{str(frame.header)}:{payload}"
        # msg = frame.tnc2
        # LOG.debug(f"Decoding {msg}")

        raw = aprslib.parse(str(frame))
        packet = core.Packet.factory(raw)
        if isinstance(packet, core.ThirdParty):
            return packet.subpacket
        else:
            return packet

    def setup_connection(self):
        self._client = kiss.KISS3Client()
        return self._client


class APRSDFakeClient(Client, metaclass=trace.TraceWrapperMetaclass):

    @staticmethod
    def is_enabled():
        if CONF.fake_client.enabled:
            return True
        return False

    @staticmethod
    def is_configured():
        return APRSDFakeClient.is_enabled()

    def is_alive(self):
        return True

    def setup_connection(self):
        return fake.APRSDFakeClient()

    @staticmethod
    def transport():
        return TRANSPORT_FAKE

    def decode_packet(self, *args, **kwargs):
        LOG.debug(f"kwargs {kwargs}")
        pkt = kwargs["packet"]
        LOG.debug(f"Got an APRS Fake Packet '{pkt}'")
        return pkt


class ClientFactory:
    _instance = None

    def __new__(cls, *args, **kwargs):
        """This magic turns this into a singleton."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            # Put any initialization here.
        return cls._instance

    def __init__(self):
        self._builders = {}

    def register(self, key, builder):
        self._builders[key] = builder

    def create(self, key=None):
        if not key:
            if APRSISClient.is_enabled():
                key = TRANSPORT_APRSIS
            elif KISSClient.is_enabled():
                key = KISSClient.transport()
            elif APRSDFakeClient.is_enabled():
                key = TRANSPORT_FAKE

        builder = self._builders.get(key)
        LOG.debug(f"Creating client {key}")
        if not builder:
            raise ValueError(key)
        return builder()

    def is_client_enabled(self):
        """Make sure at least one client is enabled."""
        enabled = False
        for key in self._builders.keys():
            try:
                enabled |= self._builders[key].is_enabled()
            except KeyError:
                pass

        return enabled

    def is_client_configured(self):
        enabled = False
        for key in self._builders.keys():
            try:
                enabled |= self._builders[key].is_configured()
            except KeyError:
                pass
            except exception.MissingConfigOptionException as ex:
                LOG.error(ex.message)
                return False
            except exception.ConfigOptionBogusDefaultException as ex:
                LOG.error(ex.message)
                return False

        return enabled

    @staticmethod
    def setup():
        """Create and register all possible client objects."""
        global factory

        factory = ClientFactory()
        factory.register(TRANSPORT_APRSIS, APRSISClient)
        factory.register(TRANSPORT_TCPKISS, KISSClient)
        factory.register(TRANSPORT_SERIALKISS, KISSClient)
        factory.register(TRANSPORT_FAKE, APRSDFakeClient)
