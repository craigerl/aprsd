import logging
from typing import Callable, Protocol, runtime_checkable

from aprsd.utils import singleton

LOG = logging.getLogger("APRSD")


@runtime_checkable
class KeepAliveProducer(Protocol):
    """The KeepAliveProducer protocol is used to define the interface for running Keepalive checks."""

    def keepalive_check(self) -> dict:
        """Check for keepalive."""
        ...

    def keepalive_log(self):
        """Log any keepalive information."""
        ...


@singleton
class KeepAliveCollector:
    """The Collector class is used to collect stats from multiple StatsProducer instances."""

    def __init__(self):
        self.producers: list[Callable] = []

    def check(self) -> None:
        """Do any keepalive checks."""
        for name in self.producers:
            cls = name()
            try:
                cls.keepalive_check()
            except Exception as e:
                LOG.error(f"Error in producer {name} (check): {e}")

    def log(self) -> None:
        """Log any relevant information during a KeepAlive check"""
        for name in self.producers:
            cls = name()
            try:
                cls.keepalive_log()
            except Exception as e:
                LOG.error(f"Error in producer {name} (check): {e}")

    def register(self, producer_name: Callable):
        if not isinstance(producer_name, KeepAliveProducer):
            raise TypeError(f"Producer {producer_name} is not a KeepAliveProducer")
        self.producers.append(producer_name)

    def unregister(self, producer_name: Callable):
        if not isinstance(producer_name, KeepAliveProducer):
            raise TypeError(f"Producer {producer_name} is not a KeepAliveProducer")
        self.producers.remove(producer_name)
