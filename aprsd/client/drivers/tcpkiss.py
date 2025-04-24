"""
APRSD KISS Client Driver using native KISS implementation.

This module provides a KISS client driver for APRSD using the new
non-asyncio KISSInterface implementation.
"""

import datetime
import logging
import select
import socket
import time
from typing import Any, Callable, Dict

import aprslib
from ax253 import frame as ax25frame
from kiss import constants as kiss_constants
from kiss import util as kissutil
from kiss.kiss import Command
from oslo_config import cfg

from aprsd import (  # noqa
    client,
    conf,  # noqa
    exception,
)
from aprsd.packets import core

CONF = cfg.CONF
LOG = logging.getLogger('APRSD')


def handle_fend(buffer: bytes, strip_df_start: bool = True) -> bytes:
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
    LOG.warning(f'handle_fend {" ".join(f"{b:02X}" for b in bytes(frame))}')
    return bytes(frame)


# class TCPKISSDriver(metaclass=trace.TraceWrapperMetaclass):
class TCPKISSDriver:
    """APRSD client driver for TCP KISS connections."""

    # Class level attributes required by Client protocol
    packets_received = 0
    packets_sent = 0
    last_packet_sent = None
    last_packet_received = None
    keepalive = None
    client_name = None
    socket = None
    # timeout in seconds
    select_timeout = 1
    path = None

    def __init__(self):
        """Initialize the KISS client.

        Args:
            client_name: Name of the client instance
        """
        super().__init__()
        self._connected = False
        self.keepalive = datetime.datetime.now()
        self._running = False
        # This is initialized in setup_connection()
        self.socket = None

    @property
    def transport(self) -> str:
        return client.TRANSPORT_TCPKISS

    @classmethod
    def is_enabled(cls) -> bool:
        """Check if KISS is enabled in configuration.

        Returns:
            bool: True if either TCP is enabled
        """
        return CONF.kiss_tcp.enabled

    @staticmethod
    def is_configured():
        # Ensure that the config vars are correctly set
        if TCPKISSDriver.is_enabled():
            if not CONF.kiss_tcp.host:
                LOG.error('KISS TCP enabled, but no host is set.')
                raise exception.MissingConfigOptionException(
                    'kiss_tcp.host is not set.',
                )
            return True
        return False

    @property
    def is_alive(self) -> bool:
        """Check if the client is connected.

        Returns:
            bool: True if connected to KISS TNC, False otherwise
        """
        return self._connected

    def close(self):
        """Close the connection."""
        self.stop()

    def send(self, packet: core.Packet):
        """Send an APRS packet.

        Args:
            packet: APRS packet to send (Packet or Message object)

        Raises:
            Exception: If not connected or send fails
        """
        if not self.socket:
            raise Exception('KISS interface not initialized')

        payload = None
        path = self.path
        packet.prepare()
        payload = packet.payload.encode('US-ASCII')
        if packet.path:
            path = packet.path

        LOG.debug(
            f"KISS Send '{payload}' TO '{packet.to_call}' From "
            f"'{packet.from_call}' with PATH '{path}'",
        )
        frame = ax25frame.Frame.ui(
            destination='APZ100',
            # destination=packet.to_call,
            source=packet.from_call,
            path=path,
            info=payload,
        )

        # now escape the frame special characters
        frame_escaped = kissutil.escape_special_codes(bytes(frame))
        # and finally wrap the frame in KISS protocol
        command = Command.DATA_FRAME
        frame_kiss = b''.join(
            [kiss_constants.FEND, command.value, frame_escaped, kiss_constants.FEND]
        )
        self.socket.send(frame_kiss)
        # Update last packet sent time
        self.last_packet_sent = datetime.datetime.now()
        # Increment packets sent counter
        self.packets_sent += 1

    def setup_connection(self):
        """Set up the KISS interface."""
        if not self.is_enabled():
            LOG.error('KISS is not enabled in configuration')
            return

        try:
            # Configure for TCP KISS
            if self.is_enabled():
                LOG.info(
                    f'KISS TCP Connection to {CONF.kiss_tcp.host}:{CONF.kiss_tcp.port}'
                )
                self.path = CONF.kiss_tcp.path
                self.connect()
            if self._connected:
                LOG.info('KISS interface initialized')
            else:
                LOG.error('Failed to connect to KISS interface')

        except Exception as ex:
            LOG.error('Failed to initialize KISS interface')
            LOG.exception(ex)
            self._connected = False

    def set_filter(self, filter_text: str):
        """Set packet filter (not implemented for KISS).

        Args:
            filter_text: Filter specification (ignored for KISS)
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

    def login_success(self) -> bool:
        """There is no login for KISS."""
        if not self._connected:
            return False
        return True

    def login_failure(self) -> str:
        """There is no login for KISS."""
        return 'Login successful'

    def consumer(self, callback: Callable, raw: bool = False):
        """Start consuming frames with the given callback.

        Args:
            callback: Function to call with received packets

        Raises:
            Exception: If not connected to KISS TNC
        """
        self._running = True
        while self._running:
            # Ensure connection
            if not self._connected:
                if not self.connect():
                    time.sleep(1)
                    continue

            # Read frame
            frame = self.read_frame()
            if frame:
                LOG.warning(f'GOT FRAME: {frame} calling {callback}')
                kwargs = {
                    'frame': frame,
                }
                callback(**kwargs)

    def decode_packet(self, *args, **kwargs) -> core.Packet:
        """Decode a packet from an AX.25 frame.

        Args:
            frame: Received AX.25 frame
        """
        frame = kwargs.get('frame')
        if not frame:
            LOG.warning('No frame received to decode?!?!')
            return None

        LOG.warning(f'FRAME: {str(frame)}')
        try:
            aprslib_frame = aprslib.parse(str(frame))
            return core.factory(aprslib_frame)
        except Exception as e:
            LOG.error(f'Error decoding packet: {e}')
            return None

    def stop(self):
        """Stop the KISS interface."""
        self._running = False
        self._connected = False
        if self.socket:
            try:
                self.socket.close()
            except Exception:
                pass

    def stats(self, serializable: bool = False) -> Dict[str, Any]:
        """Get client statistics.

        Returns:
            Dict containing client statistics
        """
        if serializable:
            keepalive = self.keepalive.isoformat()
        else:
            keepalive = self.keepalive
        stats = {
            'client': self.__class__.__name__,
            'transport': self.transport,
            'connected': self._connected,
            'path': self.path,
            'packets_sent': self.packets_sent,
            'packets_received': self.packets_received,
            'last_packet_sent': self.last_packet_sent,
            'last_packet_received': self.last_packet_received,
            'connection_keepalive': keepalive,
            'host': CONF.kiss_tcp.host,
            'port': CONF.kiss_tcp.port,
        }

        return stats

    def connect(self) -> bool:
        """Establish TCP connection to the KISS host.

        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            if self.socket:
                try:
                    self.socket.close()
                except Exception:
                    pass

            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5.0)  # 5 second timeout for connection
            self.socket.connect((CONF.kiss_tcp.host, CONF.kiss_tcp.port))
            self.socket.settimeout(0.1)  # Reset to shorter timeout for reads
            self._connected = True
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            # MACOS doesn't have TCP_KEEPIDLE
            if hasattr(socket, 'TCP_KEEPIDLE'):
                self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 1)
            self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 3)
            self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 5)
            return True

        except ConnectionError as e:
            LOG.error(
                f'Failed to connect to {CONF.kiss_tcp.host}:{CONF.kiss_tcp.port} - {str(e)}'
            )
            self._connected = False
            return False

        except Exception as e:
            LOG.error(
                f'Failed to connect to {CONF.kiss_tcp.host}:{CONF.kiss_tcp.port} - {str(e)}'
            )
            self._connected = False
            return False

    def fix_raw_frame(self, raw_frame: bytes) -> bytes:
        """Fix the raw frame by recalculating the FCS."""
        ax25_data = raw_frame[2:-1]  # Remove KISS markers
        return handle_fend(ax25_data)

    def read_frame(self, blocking=False):
        """
        Generator for complete lines, received from the server
        """
        try:
            self.socket.setblocking(0)
        except OSError as e:
            LOG.error(f'socket error when setblocking(0): {str(e)}')
            raise aprslib.ConnectionDrop('connection dropped') from e

        while self._running:
            short_buf = b''

            try:
                readable, _, _ = select.select(
                    [self.socket],
                    [],
                    [],
                    self.select_timeout,
                )
                if not readable:
                    if not blocking:
                        break
                    else:
                        continue
            except Exception as e:
                LOG.error(f'Error in read loop: {e}')
                self._connected = False
                break

            try:
                print('reading from socket')
                short_buf = self.socket.recv(1024)
                print(f'short_buf: {short_buf}')
                # sock.recv returns empty if the connection drops
                if not short_buf:
                    if not blocking:
                        # We could just not be blocking, so empty is expected
                        continue
                    else:
                        self.logger.error('socket.recv(): returned empty')
                        raise aprslib.ConnectionDrop('connection dropped')

                raw_frame = self.fix_raw_frame(short_buf)
                return ax25frame.Frame.from_bytes(raw_frame)
            except OSError as e:
                # self.logger.error("socket error on recv(): %s" % str(e))
                if 'Resource temporarily unavailable' in str(e):
                    if not blocking:
                        if len(short_buf) == 0:
                            break
            except socket.timeout:
                continue
            except (KeyboardInterrupt, SystemExit):
                raise
            except ConnectionError:
                self.close()
                if not self.auto_reconnect:
                    raise
                else:
                    self.connect()
                    continue
            except StopIteration:
                break
            except IOError:
                LOG.error('IOError')
                break
            except Exception as e:
                LOG.error(f'Error in read loop: {e}')
                self._connected = False
                if not self.auto_reconnect:
                    break
