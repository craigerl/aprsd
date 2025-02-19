from aprsd.packets import collector
from aprsd.packets.core import (  # noqa: F401
    AckPacket,
    BeaconPacket,
    BulletinPacket,
    GPSPacket,
    MessagePacket,
    MicEPacket,
    ObjectPacket,
    Packet,
    RejectPacket,
    StatusPacket,
    ThirdPartyPacket,
    UnknownPacket,
    WeatherPacket,
    factory,
)
from aprsd.packets.filter import PacketFilter
from aprsd.packets.filters.dupe_filter import DupePacketFilter
from aprsd.packets.packet_list import PacketList  # noqa: F401
from aprsd.packets.seen_list import SeenList  # noqa: F401
from aprsd.packets.tracker import PacketTrack  # noqa: F401
from aprsd.packets.watch_list import WatchList  # noqa: F401

# Register all the packet tracking objects.
collector.PacketCollector().register(PacketList)
collector.PacketCollector().register(SeenList)
collector.PacketCollector().register(PacketTrack)
collector.PacketCollector().register(WatchList)

# Register all the packet filters for normal processing
# For specific commands you can deregister these if you don't want them.
PacketFilter().register(DupePacketFilter)


NULL_MESSAGE = -1
