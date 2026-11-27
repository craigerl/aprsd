import logging
from typing import Callable, Protocol, runtime_checkable

from aprsd.packets import core
from aprsd.utils import singleton

LOG = logging.getLogger('APRSD')


@runtime_checkable
class PacketMonitor(Protocol):
    """Protocol for Monitoring packets in some way."""

    def is_enabled(self) -> bool:
        """Whether this monitor should see rx/tx/load."""
        ...

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

    @staticmethod
    def _check_monitor(monitor: Callable) -> None:
        if isinstance(monitor, PacketMonitor):
            return
        missing = [
            attr for attr in ('rx', 'tx', 'flush', 'load') if not hasattr(monitor, attr)
        ]
        if missing:
            raise TypeError(
                f'Monitor {monitor} is not a PacketMonitor '
                f'(missing {", ".join(missing)})'
            )
        # Monitors written before is_enabled() existed still register; the
        # loops treat a missing method as enabled.
        LOG.warning(
            f'Monitor {monitor} does not implement is_enabled(); assuming it is enabled'
        )

    def register(self, monitor: Callable) -> None:
        self._check_monitor(monitor)
        self.monitors.append(monitor)

    def unregister(self, monitor: Callable) -> None:
        self._check_monitor(monitor)
        self.monitors.remove(monitor)

    def rx(self, packet: type[core.Packet]) -> None:
        for name in self.monitors:
            cls = name()
            try:
                is_enabled = getattr(cls, 'is_enabled', None)
                if is_enabled is not None and not is_enabled():
                    continue
                cls.rx(packet)
            except Exception as e:
                LOG.error(f'Error in monitor {name} (rx): {e}')

    def tx(self, packet: type[core.Packet]) -> None:
        for name in self.monitors:
            cls = name()
            try:
                is_enabled = getattr(cls, 'is_enabled', None)
                if is_enabled is not None and not is_enabled():
                    continue
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
            try:
                is_enabled = getattr(cls, 'is_enabled', None)
                if is_enabled is not None and not is_enabled():
                    continue
                cls.load()
            except Exception as e:
                LOG.error(f'Error in monitor {name} (load): {e}')
