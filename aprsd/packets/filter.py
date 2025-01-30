import logging
from typing import Callable, Protocol, runtime_checkable, Union, Dict

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
        self.filters: Dict[str, Callable] = {}

    def register(self, packet_filter: Callable) -> None:
        if not isinstance(packet_filter, PacketFilterProtocol):
            raise TypeError(f"class {packet_filter} is not a PacketFilterProtocol object")

        if packet_filter not in self.filters:
            self.filters[packet_filter] = packet_filter()

    def unregister(self, packet_filter: Callable) -> None:
        if not isinstance(packet_filter, PacketFilterProtocol):
            raise TypeError(f"class {packet_filter} is not a PacketFilterProtocol object")
        if packet_filter in self.filters:
            del self.filters[packet_filter]

    def filter(self, packet: type[core.Packet]) -> Union[type[core.Packet], None]:
        """Run through each of the filters.

        This will step through each registered filter class
        and call filter on it.

        If the filter object returns None, we are done filtering.
        If the filter object returns the packet, we continue filtering.
        """
        for packet_filter in self.filters:
            try:
                if not self.filters[packet_filter].filter(packet):
                    LOG.debug(f"{self.filters[packet_filter].__class__.__name__} dropped {packet.__class__.__name__}:{packet.human_info}")
                    return None
            except Exception as ex:
                LOG.error(f"{packet_filter.__clas__.__name__} failed filtering packet {packet.__class__.__name__} : {ex}")
        return packet
