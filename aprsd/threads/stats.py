import logging
import time

from oslo_config import cfg

from aprsd.stats import collector
from aprsd.threads import APRSDThread
from aprsd.utils import objectstore

CONF = cfg.CONF
LOG = logging.getLogger('APRSD')


class StatsStore(objectstore.ObjectStoreMixin):
    """Container to save the stats from the collector."""

    def add(self, stats: dict):
        with self.lock:
            self.data = stats


class APRSDStatsStoreThread(APRSDThread):
    """Save APRSD Stats to disk periodically."""

    # how often in seconds to write the file
    save_interval = 10

    def __init__(self):
        super().__init__('StatsStore')

    def loop(self):
        if self.loop_count % self.save_interval == 0:
            stats = collector.Collector().collect()
            ss = StatsStore()
            ss.add(stats)
            ss.save()

        time.sleep(1)
        return True
