import logging
from typing import Union

from oslo_config import cfg

from aprsd import packets
from aprsd.packets import core
from aprsd.utils import singleton

CONF = cfg.CONF
LOG = logging.getLogger('APRSD')


@singleton
class PacketTypeFilter:
    """This filter is used to filter out packets that don't match a specific type.

    To use this, register it with the PacketFilter class,
    then instante it and call set_allow_list() with a list of packet types
    you want to allow to pass the filtering.  All other packets will be
    filtered out.
    """

    filters = {
        packets.Packet.__name__: packets.Packet,
        packets.AckPacket.__name__: packets.AckPacket,
        packets.BeaconPacket.__name__: packets.BeaconPacket,
        packets.GPSPacket.__name__: packets.GPSPacket,
        packets.MessagePacket.__name__: packets.MessagePacket,
        packets.MicEPacket.__name__: packets.MicEPacket,
        packets.ObjectPacket.__name__: packets.ObjectPacket,
        packets.StatusPacket.__name__: packets.StatusPacket,
        packets.ThirdPartyPacket.__name__: packets.ThirdPartyPacket,
        packets.WeatherPacket.__name__: packets.WeatherPacket,
        packets.UnknownPacket.__name__: packets.UnknownPacket,
    }

    allow_list = ()

    def set_allow_list(self, filter_list):
        tmp_list = []
        for filter in filter_list:
            LOG.warning(
                f'Setting filter {filter} : {self.filters[filter]} to tmp {tmp_list}'
            )
            tmp_list.append(self.filters[filter])
        self.allow_list = tuple(tmp_list)

    def filter(self, packet: type[core.Packet]) -> Union[type[core.Packet], None]:
        """Only allow packets of certain types to filter through."""
        if self.allow_list:
            if isinstance(packet, self.allow_list):
                return packet
