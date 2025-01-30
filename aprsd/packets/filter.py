import logging
from typing import Callable, Protocol, runtime_checkable

from aprsd.packets import core
from aprsd.utils import singleton


LOG = logging.getLogger("APRSD")


@runtime_checkable
class PacketFilterProtocol(Protocol):
    """Protocol API for a packet filter class.
    """
    def filter(self, packet: type[core.Packet]) -> Union[type[core.Packet], None]:
        """When we get a packet from the network.

        Return a Packet object if the filter passes. Return None if the 
        Packet is filtered out.
        """
        ...


@singleton
class PacketFilter:
    def __init__(self):
        self.filters = list[Callable] = []

    def register(self, packet_filter: Callable) -> None:
        if not isinstance(packet_filter, PacketFilterProtocol):
            raise TypeError(f"class {packet_filter} is not a PacketFilterProtocol object")
        self.filters.append(packet_filter)

    def unregister(self, packet_filter: Callable) -> None:
        if not isinstance(packet_filter, PacketFilterProtocol):
            raise TypeError(f"class {packet_filter} is not a PacketFilterProtocol object")
        self.filters.remove(packet_filter)

    def filter(self, packet: type[core.Packet]) -> Union[type[core.Packet], None]:
        """Run through each of the filters.

        This will step through each registered filter class
        and call filter on it.

        If the filter object returns None, we are done filtering.
        If the filter object returns the packet, we continue filtering.
        """
        for name in self.filters:
            cls = name()
            try:
                packet = cls.filter(packet)
            except Exception as ex:
                LOG.error(f"Error in fitering packet {packet} with filter class {name}")
            if not packet:
                return None
        return packet
