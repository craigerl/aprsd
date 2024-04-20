import logging
from typing import Callable, Protocol, runtime_checkable

from aprsd.packets import core
from aprsd.utils import singleton


LOG = logging.getLogger("APRSD")


@runtime_checkable
class PacketMonitor(Protocol):
    """Protocol for Monitoring packets in some way."""

    def rx(self, packet: type[core.Packet]) -> None:
        """When we get a packet from the network."""
        ...

    def tx(self, packet: type[core.Packet]) -> None:
        """When we send a packet out the network."""
        ...


@singleton
class PacketCollector:
    def __init__(self):
        self.monitors: list[Callable] = []

    def register(self, monitor: Callable) -> None:
        self.monitors.append(monitor)

    def unregister(self, monitor: Callable) -> None:
        self.monitors.remove(monitor)

    def rx(self, packet: type[core.Packet]) -> None:
        for name in self.monitors:
            cls = name()
            if isinstance(cls, PacketMonitor):
                try:
                    cls.rx(packet)
                except Exception as e:
                    LOG.error(f"Error in monitor {name} (rx): {e}")

            else:
                raise TypeError(f"Monitor {name} is not a PacketMonitor")

    def tx(self, packet: type[core.Packet]) -> None:
        for name in self.monitors:
            cls = name()
            if isinstance(cls, PacketMonitor):
                try:
                    cls.tx(packet)
                except Exception as e:
                    LOG.error(f"Error in monitor {name} (tx): {e}")
            else:
                raise TypeError(f"Monitor {name} is not a PacketMonitor")
