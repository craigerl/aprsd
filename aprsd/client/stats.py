import threading

import wrapt
from oslo_config import cfg

from aprsd.client.client import APRSDClient
from aprsd.utils import singleton

CONF = cfg.CONF


@singleton
class APRSClientStats:
    lock = threading.Lock()

    @wrapt.synchronized(lock)
    def stats(self, serializable=False):
        return APRSDClient().stats(serializable=serializable)
