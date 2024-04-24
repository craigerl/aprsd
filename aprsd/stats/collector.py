import logging
from typing import Callable, Protocol, runtime_checkable

from aprsd.utils import singleton


LOG = logging.getLogger("APRSD")


@runtime_checkable
class StatsProducer(Protocol):
    """The StatsProducer protocol is used to define the interface for collecting stats."""
    def stats(self, serializeable=False) -> dict:
        """provide stats in a dictionary format."""
        ...


@singleton
class Collector:
    """The Collector class is used to collect stats from multiple StatsProducer instances."""
    def __init__(self):
        self.producers: list[Callable] = []

    def collect(self, serializable=False) -> dict:
        stats = {}
        for name in self.producers:
            cls = name()
            if isinstance(cls, StatsProducer):
                try:
                    stats[cls.__class__.__name__] = cls.stats(serializable=serializable).copy()
                except Exception as e:
                    LOG.error(f"Error in producer {name} (stats): {e}")
            else:
                raise TypeError(f"{cls} is not an instance of StatsProducer")
        return stats

    def register_producer(self, producer_name: Callable):
        self.producers.append(producer_name)
