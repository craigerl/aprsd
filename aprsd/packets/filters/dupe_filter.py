import logging
from collections import OrderedDict
from typing import Union

from oslo_config import cfg

from aprsd.packets import core

CONF = cfg.CONF
LOG = logging.getLogger('APRSD')


class DupePacketFilter:
    """This is a packet filter to detect duplicate packets.

    Keeps its own time window of already seen packets.  If a packet
    is seen again and the stored copy was already processed within
    ``packet_dupe_timeout`` seconds, it's a dupe.

    The window is time based on purpose: ``PacketList`` only keeps
    ``packet_list_maxlen`` packets, which at normal RF rates covers far
    less than ``packet_dupe_timeout`` seconds (#320).

    ``_seen`` therefore holds about ``packet_dupe_timeout`` seconds worth
    of packets with a msgNo (RX rate x timeout), so memory grows with the
    packet rate instead of being capped at ``packet_list_maxlen``.
    """

    def __init__(self):
        # packet.key -> packet.  Ordered oldest first so pruning is cheap.
        # We keep the packet object, not a copy, because ``processed`` is
        # set on it later by the processing thread.
        self._seen: OrderedDict = OrderedDict()

    def _prune(self, now: float) -> None:
        """Drop entries that fell out of the dupe window."""
        timeout = CONF.packet_dupe_timeout
        while self._seen:
            key = next(iter(self._seen))
            if now - self._seen[key].timestamp < timeout:
                break
            del self._seen[key]

    def filter(self, packet: type[core.Packet]) -> Union[type[core.Packet], None]:
        """Filter a packet out if it's already been seen and processed."""
        if isinstance(packet, core.AckPacket):
            # We don't need to drop AckPackets, those should be
            # processed.
            # Send the AckPacket to the queue for processing elsewhere.
            return packet

        if not packet.msgNo:
            # If the packet doesn't have a message id
            # then there is no reliable way to detect
            # if it's a dupe, so we just pass it on.
            # it shouldn't get acked either.
            return packet

        # Find the packet in the list of already seen packets
        # Based on the packet.key
        found = self._seen.get(packet.key)

        if found is not None:
            if not found.processed:
                # The previously seen packet hasn't been processed yet,
                # so let this one through too.
                return packet
            if abs(packet.timestamp - found.timestamp) < CONF.packet_dupe_timeout:
                # If the packet came in within N seconds of the
                # Last time seeing the packet, then we drop it as a dupe.
                LOG.warning(
                    f'Packet {packet.from_call}:{packet.msgNo} already tracked, dropping.'
                )
                return None
            LOG.warning(
                f'Packet {packet.from_call}:{packet.msgNo} already tracked '
                f'but older than {CONF.packet_dupe_timeout} seconds. processing.',
            )

        # Remember this copy.  Processing marks it when it's handled.
        self._prune(packet.timestamp)
        self._seen[packet.key] = packet
        self._seen.move_to_end(packet.key)
        return packet
