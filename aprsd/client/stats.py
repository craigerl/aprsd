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
        return client.client_factory.create().stats(serializable=serializable)
