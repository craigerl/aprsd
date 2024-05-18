import threading

from oslo_config import cfg
import wrapt

from aprsd import client
from aprsd.utils import singleton


CONF = cfg.CONF


@singleton
class APRSClientStats:

    lock = threading.Lock()

    @wrapt.synchronized(lock)
    def stats(self, serializable=False):
        cl = client.client_factory.create()
        stats = {
            "transport": cl.transport(),
            "filter": cl.filter,
            "connected": cl.connected,
        }

        if cl.transport() == client.TRANSPORT_APRSIS:
            stats["server_string"] = cl.client.server_string
            keepalive = cl.client.aprsd_keepalive
            if serializable:
                keepalive = keepalive.isoformat()
            stats["server_keepalive"] = keepalive
        elif cl.transport() == client.TRANSPORT_TCPKISS:
            stats["host"] = CONF.kiss_tcp.host
            stats["port"] = CONF.kiss_tcp.port
        elif cl.transport() == client.TRANSPORT_SERIALKISS:
            stats["device"] = CONF.kiss_serial.device
        return stats
