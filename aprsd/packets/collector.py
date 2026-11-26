import logging
from typing import Callable, Protocol, runtime_checkable

from aprsd.packets import core
from aprsd.utils import singleton

LOG = logging.getLogger('APRSD')


@runtime_checkable
class PacketMonitor(Protocol):
    """Protocol for Monitoring packets in some way."""

    def rx(self, packet: type[core.Packet]) -> None:
        """When we get a packet from the network."""
        ...

    def tx(self, packet: type[core.Packet]) -> None:
        """When we send a packet out the network."""
        ...

    def flush(self) -> None:
        """Flush out any data."""
        ...

    def load(self) -> None:
        """Load any data."""
        ...


@singleton
class PacketCollector:
    def __init__(self):
        self.monitors: list[Callable] = []

    def register(self, monitor: Callable) -> None:
        if not isinstance(monitor, PacketMonitor):
            raise TypeError(f'Monitor {monitor} is not a PacketMonitor')
        self.monitors.append(monitor)

    def unregister(self, monitor: Callable) -> None:
        if not isinstance(monitor, PacketMonitor):
            raise TypeError(f'Monitor {monitor} is not a PacketMonitor')
        self.monitors.remove(monitor)

    def _is_enabled(self, monitor) -> bool:
        """Honor a monitor's is_enabled(), the way the client driver registry does.

        Monitors without the method are always enabled.
        """
        check = getattr(monitor, 'is_enabled', None)
        return True if check is None else check()

    def rx(self, packet: type[core.Packet]) -> None:
        for name in self.monitors:
            cls = name()
            if not self._is_enabled(cls):
                continue
            try:
                cls.rx(packet)
            except Exception as e:
                LOG.error(f'Error in monitor {name} (rx): {e}')

    def tx(self, packet: type[core.Packet]) -> None:
        for name in self.monitors:
            cls = name()
            if not self._is_enabled(cls):
                continue
            try:
                cls.tx(packet)
            except Exception as e:
                LOG.error(f'Error in monitor {name} (tx): {e}')

    def flush(self):
        """Call flush on the objects. This is used to flush out any data."""
        for name in self.monitors:
            cls = name()
            try:
                cls.flush()
            except Exception as e:
                LOG.error(f'Error in monitor {name} (flush): {e}')

    def load(self):
        """Call load on the objects. This is used to load any data."""
        for name in self.monitors:
            cls = name()
            if not self._is_enabled(cls):
                continue
            try:
                cls.load()
            except Exception as e:
                LOG.error(f'Error in monitor {name} (load): {e}')
