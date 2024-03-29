import datetime
import tracemalloc

from oslo_config import cfg

import aprsd
from aprsd import utils


CONF = cfg.CONF


@utils.singleton
class APRSDStats:
    """The AppStats class is used to collect stats from the application."""
    def __init__(self):
        self.start_time = datetime.datetime.now()

    @property
    def uptime(self):
        return datetime.datetime.now() - self.start_time

    def stats(self) -> dict:
        current, peak = tracemalloc.get_traced_memory()
        stats = {
            "version": aprsd.__version__,
            "uptime": self.uptime,
            "callsign": CONF.callsign,
            "memory_current": int(current),
            "memory_current_str": utils.human_size(current),
            "memory_peak": int(peak),
            "memory_peak_str": utils.human_size(peak),
        }
        return stats
