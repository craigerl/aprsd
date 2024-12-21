import logging

from oslo_config import cfg

from aprsd import client
from aprsd.client import base
from aprsd.client.drivers import fake as fake_driver
from aprsd.utils import trace

CONF = cfg.CONF
LOG = logging.getLogger("APRSD")


class APRSDFakeClient(base.APRSClient, metaclass=trace.TraceWrapperMetaclass):
    def stats(self, serializable=False) -> dict:
        return {
            "transport": "Fake",
            "connected": True,
        }

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

    def close(self):
        pass

    def setup_connection(self):
        self.connected = True
        return fake_driver.APRSDFakeClient()

    @staticmethod
    def transport():
        return client.TRANSPORT_FAKE

    def decode_packet(self, *args, **kwargs):
        LOG.debug(f"kwargs {kwargs}")
        pkt = kwargs["packet"]
        LOG.debug(f"Got an APRS Fake Packet '{pkt}'")
        return pkt
