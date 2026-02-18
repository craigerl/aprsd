"""
APRSD KISS Client Driver Base classusing native KISS implementation.

This module provides a KISS client driver for APRSD using the new
non-asyncio KISSInterface implementation.
"""

import datetime
import logging
from typing import Any, Callable

import aprslib
from kiss import util as kissutil

from aprsd.packets import core
from aprsd.utils import trace

LOG = logging.getLogger('APRSD')


class KISSDriver(metaclass=trace.TraceWrapperMetaclass):
    """APRSD KISS Client Driver Base class."""

    packets_received = 0
    packets_sent = 0
    last_packet_sent = None
    last_packet_received = None
    _keepalive = None

    # timeout in seconds
    select_timeout = 1

    def __init__(self):
        """Initialize the KISS client.

        Args:
            client_name: Name of the client instance
        """
        super().__init__()
        self._connected = False
        self._keepalive = datetime.datetime.now()

    @property
    def keepalive(self) -> datetime.datetime:
        """Get the keepalive timestamp.

        Returns:
            datetime.datetime: Last keepalive timestamp
        """
        return self._keepalive

    def login_success(self) -> bool:
        """There is no login for KISS."""
        if not self._connected:
            return False
        return True

    def login_failure(self) -> str:
        """There is no login for KISS."""
        return 'Login successful'

    def set_filter(self, filter: str) -> None:
        """Set packet filter (not implemented for KISS).

        Args:
            filter: Filter specification (ignored for KISS)
        """
        # KISS doesn't support filtering at the TNC level
        pass

    @property
    def filter(self) -> str:
        """Get packet filter (not implemented for KISS).
        Returns:
            str: Empty string (not implemented for KISS)
        """
        return ''

    @property
    def is_alive(self) -> bool:
        """Check if the client is connected.

        Returns:
            bool: True if connected to KISS TNC, False otherwise
        """
        return self._connected

    def _handle_fend(self, buffer: bytes, strip_df_start: bool = True) -> bytes:
        """
        Handle FEND (end of frame) encountered in a KISS data stream.

        :param buffer: the buffer containing the frame
        :param strip_df_start: remove leading null byte (DATA_FRAME opcode)
        :return: the bytes of the frame without escape characters or frame
                end markers (FEND)
        """
        frame = kissutil.recover_special_codes(kissutil.strip_nmea(bytes(buffer)))
        if strip_df_start:
            frame = kissutil.strip_df_start(frame)
        return bytes(frame)

    def fix_raw_frame(self, raw_frame: bytes) -> bytes:
        """Fix the raw frame by recalculating the FCS."""
        ax25_data = raw_frame[2:-1]  # Remove KISS markers
        return self._handle_fend(ax25_data)

    def decode_packet(self, *args, **kwargs) -> core.Packet:
        """Decode a packet from an AX.25 frame.

        Args:
            frame: Received AX.25 frame
        """
        if not args:
            LOG.warning('No frame received to decode?!?!')
            return None

        frame = args[0]

        try:
            aprslib_frame = aprslib.parse(str(frame))
            packet = core.factory(aprslib_frame)
            if isinstance(packet, core.ThirdPartyPacket):
                return packet.subpacket
            else:
                return packet
        except Exception as e:
            LOG.error(f'Error decoding packet: {e}')
            return None

    def consumer(self, callback: Callable, raw: bool = False):
        """Start consuming frames with the given callback.

        Args:
            callback: Function to call with received packets.
                     Called with frame=<frame> keyword argument to match
                     the signature used by other drivers (packet=<packet>).
            raw: If True, callback receives raw frame data.
                 If False, callback receives decoded packet.

        Raises:
            Exception: If not connected to KISS TNC

        Note:
            The callback signature should accept keyword arguments:
            - For raw frames: callback(frame=frame_obj)
            - For decoded packets: callback(packet=packet_obj)
        """
        # Ensure connection
        if not self._connected:
            return

        # Read frame
        frame = self.read_frame()
        if frame:
            LOG.info(f'GOT FRAME: {frame} calling {callback}')
            if raw:
                # Pass raw frame with keyword argument for consistency
                callback(frame=frame)
            else:
                # Decode frame to packet and pass with keyword argument
                packet = self.decode_packet(frame)
                if packet:
                    callback(packet=packet)

    def read_frame(self):
        """Read a frame from the KISS interface.

        This is implemented in the subclass.

        """
        raise NotImplementedError('read_frame is not implemented for KISS')

    @trace.no_trace
    def stats(self, serializable: bool = False) -> dict[str, Any]:
        """Get client statistics.

        Returns:
            Dict containing client statistics
        """
        if serializable:
            keepalive = self._keepalive.isoformat() if self._keepalive else 'None'
            if self.last_packet_sent:
                last_packet_sent = self.last_packet_sent.isoformat()
            else:
                last_packet_sent = 'None'
            if self.last_packet_received:
                last_packet_received = self.last_packet_received.isoformat()
            else:
                last_packet_received = 'None'
        else:
            keepalive = self._keepalive
            last_packet_sent = self.last_packet_sent
            last_packet_received = self.last_packet_received

        stats = {
            'client': self.__class__.__name__,
            'transport': self.transport(),
            'connected': self._connected,
            'path': self.path,
            'packets_sent': self.packets_sent,
            'packets_received': self.packets_received,
            'last_packet_sent': last_packet_sent,
            'last_packet_received': last_packet_received,
            'connection_keepalive': keepalive,
        }

        return stats
