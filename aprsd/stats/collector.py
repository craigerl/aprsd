import logging
from typing import Callable, Protocol, runtime_checkable

from aprsd.utils import singleton

LOG = logging.getLogger("APRSD")


@runtime_checkable
class StatsProducer(Protocol):
    """The StatsProducer protocol is used to define the interface for collecting stats."""

    def stats(self, serializable=False) -> dict:
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
            try:
                stats[cls.__class__.__name__] = cls.stats(
                    serializable=serializable
                ).copy()
            except Exception as e:
                LOG.error(f"Error in producer {name} (stats): {e}")
        return stats

    def register_producer(self, producer_name: Callable):
        if not isinstance(producer_name, StatsProducer):
            raise TypeError(f"Producer {producer_name} is not a StatsProducer")
        self.producers.append(producer_name)

    def unregister_producer(self, producer_name: Callable):
        if not isinstance(producer_name, StatsProducer):
            raise TypeError(f"Producer {producer_name} is not a StatsProducer")
        self.producers.remove(producer_name)
