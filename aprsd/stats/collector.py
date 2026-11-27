import logging
from typing import Callable, Protocol, runtime_checkable

from aprsd.utils import singleton

LOG = logging.getLogger('APRSD')


@runtime_checkable
class StatsProducer(Protocol):
    """The StatsProducer protocol is used to define the interface for collecting stats."""

    def stats(self, serializable=False) -> dict:
        """provide stats in a dictionary format."""
        ...

    def is_enabled(self) -> bool:
        """Whether this producer is part of the collected stats."""
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
            if not cls.is_enabled():
                continue
            try:
                stats[cls.__class__.__name__] = cls.stats(
                    serializable=serializable
                ).copy()
            except Exception as e:
                # A single failing producer must not kill the caller (the
                # KeepAliveThread calls collect() in its loop).  Log and
                # continue with the remaining producers.
                LOG.error(f'Error in producer {name} (stats): {e}')
        return stats

    def register_producer(self, producer_name: Callable):
        if not isinstance(producer_name, StatsProducer):
            missing = [
                attr
                for attr in ('stats', 'is_enabled')
                if not hasattr(producer_name, attr)
            ]
            detail = f' (missing {", ".join(missing)})' if missing else ''
            raise TypeError(f'Producer {producer_name} is not a StatsProducer{detail}')
        self.producers.append(producer_name)

    def unregister_producer(self, producer_name: Callable):
        if not isinstance(producer_name, StatsProducer):
            raise TypeError(f'Producer {producer_name} is not a StatsProducer')
        self.producers.remove(producer_name)

    def stop_all(self):
        """Stop and unregister all registered stats producers."""
        for producer in self.producers[:]:
            LOG.info(f'Stopping Stats producer {producer}')
            self.unregister_producer(producer)
