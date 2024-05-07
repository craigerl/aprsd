import datetime
import tracemalloc

from oslo_config import cfg

import aprsd
from aprsd import utils
from aprsd.log import log as aprsd_log


CONF = cfg.CONF


class APRSDStats:
    """The AppStats class is used to collect stats from the application."""

    _instance = None
    start_time = None

    def __new__(cls, *args, **kwargs):
        """Have to override the new method to make this a singleton

        instead of using @singletone decorator so the unit tests work.
        """
        if not cls._instance:
            cls._instance = super().__new__(cls)
            cls._instance.start_time = datetime.datetime.now()
        return cls._instance

    def uptime(self):
        return datetime.datetime.now() - self.start_time

    def stats(self, serializable=False) -> dict:
        current, peak = tracemalloc.get_traced_memory()
        uptime = self.uptime()
        qsize = aprsd_log.logging_queue.qsize()
        if serializable:
            uptime = str(uptime)
        stats = {
            "version": aprsd.__version__,
            "uptime": uptime,
            "callsign": CONF.callsign,
            "memory_current": int(current),
            "memory_current_str": utils.human_size(current),
            "memory_peak": int(peak),
            "memory_peak_str": utils.human_size(peak),
            "loging_queue": qsize,
        }
        return stats
