import logging
from typing import Union

from oslo_config import cfg

from aprsd import packets
from aprsd.packets import core

CONF = cfg.CONF
LOG = logging.getLogger('APRSD')


class DupePacketFilter:
    """This is a packet filter to detect duplicate packets.

    This Uses the PacketList object to see if a packet exists
    already.  If it does exist in the PacketList, then we need to
    check the flag on the packet to see if it's been processed before.
    If the packet has been processed already within the allowed
    timeframe, then it's a dupe.
    """

    def filter(self, packet: type[core.Packet]) -> Union[type[core.Packet], None]:
        # LOG.debug(f"{self.__class__.__name__}.filter called for packet {packet}")
        """Filter a packet out if it's already been seen and processed."""
        if isinstance(packet, core.AckPacket):
            # We don't need to drop AckPackets, those should be
            # processed.
            # Send the AckPacket to the queue for processing elsewhere.
            return packet
        else:
            # Make sure we aren't re-processing the same packet
            # For RF based APRS Clients we can get duplicate packets
            # So we need to track them and not process the dupes.
            pkt_list = packets.PacketList()
            found = False
            try:
                # Find the packet in the list of already seen packets
                # Based on the packet.key
                found = pkt_list.find(packet)
                if not packet.msgNo:
                    # If the packet doesn't have a message id
                    # then there is no reliable way to detect
                    # if it's a dupe, so we just pass it on.
                    # it shouldn't get acked either.
                    found = False
            except KeyError:
                found = False

            if not found:
                # We haven't seen this packet before, so we process it.
                return packet

            if not packet.processed:
                # We haven't processed this packet through the plugins.
                return packet
            elif packet.timestamp - found.timestamp < CONF.packet_dupe_timeout:
                # If the packet came in within N seconds of the
                # Last time seeing the packet, then we drop it as a dupe.
                LOG.warning(
                    f'Packet {packet.from_call}:{packet.msgNo} already tracked, dropping.'
                )
            else:
                LOG.warning(
                    f'Packet {packet.from_call}:{packet.msgNo} already tracked '
                    f'but older than {CONF.packet_dupe_timeout} seconds. processing.',
                )
                return packet
