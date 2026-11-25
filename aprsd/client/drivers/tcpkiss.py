"""
APRSD KISS Client Driver using native KISS implementation.

This module provides a KISS client driver for APRSD using the new
non-asyncio KISSInterface implementation.
"""

import datetime
import errno
import logging
import select
import socket
import threading
import time
from typing import Any

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
from aprsd.client.drivers.kiss_common import KISSDriver
from aprsd.packets import core

CONF = cfg.CONF
LOG = logging.getLogger('APRSD')


class TCPKISSDriver(KISSDriver):
    # class TCPKISSDriver:
    """APRSD client driver for TCP KISS connections."""

    _instance = None

    # Class level attributes required by Client protocol
    client_name = None
    socket = None
    path = None
    # Reconnect when the TNC restarts and this socket dies.
    # read_frame already referenced this and never defined it.
    auto_reconnect = True
    _reconnect_lock = None

    def __new__(cls, *args, **kwargs):
        """This magic turns this into a singleton."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the KISS client.

        Args:
            client_name: Name of the client instance
        """
        super().__init__()
        self._connected = False
        # keepalive is set in parent KISSDriver.__init__()
        # This is initialized in setup_connection()
        self.socket = None
        if self._reconnect_lock is None:
            self._reconnect_lock = threading.Lock()

    @staticmethod
    def transport() -> str:
        return client.TRANSPORT_TCPKISS

    @staticmethod
    def is_enabled() -> bool:
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

    def close(self) -> None:
        """Close the TCP KISS connection."""
        self._connected = False
        if self.socket:
            try:
                self.socket.close()
                LOG.info('Closing TCPKISSDriver')
            except Exception as e:
                LOG.error(f'Error closing TCP KISS socket: {e}')

    def _drop_socket(self) -> None:
        """Forget the current socket. The peer is gone or we are replacing it."""
        self._connected = False
        sock = self.socket
        self.socket = None
        if sock is not None:
            try:
                sock.close()
            except Exception:
                pass

    def _socket_is_dead(self, exc: BaseException) -> bool:
        if isinstance(
            exc, (BrokenPipeError, ConnectionResetError, ConnectionAbortedError)
        ):
            return True
        return isinstance(exc, OSError) and getattr(exc, 'errno', None) in {
            errno.EPIPE,
            errno.ECONNRESET,
            errno.ENOTCONN,
            errno.EBADF,
            errno.ECONNABORTED,
        }

    def _reconnect(self, attempts: int = 5) -> bool:
        """Close a dead KISS socket and connect again, once per second."""
        if self._reconnect_lock is None:
            self._reconnect_lock = threading.Lock()
        with self._reconnect_lock:
            self._drop_socket()
            for attempt in range(1, attempts + 1):
                if self.connect():
                    # connect() leaves a 0.1s timeout. The read loop
                    # expects a non-blocking socket.
                    try:
                        if self.socket is not None:
                            self.socket.setblocking(0)
                    except OSError as exc:
                        LOG.warning(f'KISS socket would not go non-blocking ({exc})')
                        self._drop_socket()
                    else:
                        LOG.warning(
                            'Reconnected TCP KISS to '
                            f'{CONF.kiss_tcp.host}:{CONF.kiss_tcp.port} '
                            f'(attempt {attempt})'
                        )
                        return True
                if attempt < attempts:
                    time.sleep(1)
        LOG.error(f'TCP KISS reconnect failed after {attempts} attempts')
        return False

    def _read_lost(self, exc: BaseException | None = None) -> None:
        """Reconnect after a read loses the socket, or raise if that fails."""
        if self.auto_reconnect and self._reconnect():
            return
        self._connected = False
        if exc is None:
            raise aprslib.ConnectionDrop('connection dropped')
        raise aprslib.ConnectionDrop('connection dropped') from exc

    def _send_bytes(self, frame_kiss: bytes) -> None:
        """Send one KISS frame, reconnecting once if the socket has died."""
        # Keep the socket object we checked. The read thread can set
        # self.socket to None while this runs, and None.send is an
        # AttributeError that the OSError handler would miss.
        sock = self.socket
        if not self._connected or sock is None:
            if not (self.auto_reconnect and self._reconnect()):
                raise aprslib.ConnectionDrop('KISS interface not connected')
            sock = self.socket
            if sock is None:
                raise aprslib.ConnectionDrop('KISS interface not connected')
        try:
            sock.send(frame_kiss)
        except OSError as exc:
            if not self._socket_is_dead(exc) or not self.auto_reconnect:
                raise
            LOG.warning(f'KISS send failed ({exc}); reconnecting')
            if not self._reconnect():
                raise
            sock = self.socket
            if sock is None:
                raise aprslib.ConnectionDrop('KISS interface not connected') from exc
            sock.send(frame_kiss)

    def send(self, packet: core.Packet) -> bool:
        """Send an APRS packet.

        Args:
            packet: APRS packet to send (Packet or Message object)

        Returns:
            bool: True if packet was sent successfully

        Raises:
            Exception: If not connected or send fails
        """
        if not self._connected or not self.socket:
            if not (self.auto_reconnect and self._reconnect()):
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
        self._send_bytes(frame_kiss)
        # Update last packet sent time
        self.last_packet_sent = datetime.datetime.now()
        # Increment packets sent counter
        self.packets_sent += 1
        return True

    def setup_connection(self):
        """Set up the KISS interface.

        This is the Protocol-defined method that initializes the connection.
        It internally calls connect() to establish the actual TCP connection.

        Note:
            This method follows the ClientDriver Protocol. Use this method
            for standard connection setup. The connect() method is an internal
            KISS-specific helper for establishing the TCP socket connection.
        """
        if not self.is_enabled():
            LOG.error('KISS is not enabled in configuration')
            return

        if self._connected:
            LOG.warning('KISS interface already connected')
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

    def stats(self, serializable: bool = False) -> dict[str, Any]:
        """Get client statistics.

        Returns:
            Dict containing client statistics
        """
        stats = super().stats(serializable=serializable)
        stats['host'] = CONF.kiss_tcp.host
        stats['port'] = CONF.kiss_tcp.port
        return stats

    def connect(self) -> bool:
        """Establish TCP connection to the KISS host.

        This is a KISS-specific internal method that handles the low-level
        socket connection. It is called by setup_connection().

        Note:
            This method is NOT part of the ClientDriver Protocol. It is specific
            to KISS drivers and handles TCP socket establishment and configuration.
            External code should use setup_connection() instead.

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

    def read_frame(self, blocking=False):
        """
        Generator for complete lines, received from the server
        """
        if not self.socket:
            return None

        if not self._connected:
            return None

        try:
            self.socket.setblocking(0)
        except OSError as e:
            LOG.error(f'socket error when setblocking(0): {str(e)}')
            raise aprslib.ConnectionDrop('connection dropped') from e

        while self._connected:
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
                # No need to log if we are not running.
                # this happens when the client is stopped/closed.
                LOG.error(f'Error in read loop: {e}')
                self._connected = False
                break

            try:
                short_buf = self.socket.recv(1024)
                # Empty means the peer closed the socket, not "no data yet".
                # A non-blocking socket raises BlockingIOError when it has
                # nothing to read. b'' is an orderly shutdown in both modes.
                if not short_buf:
                    LOG.warning('KISS peer closed the connection')
                    raise aprslib.ConnectionDrop('connection dropped')

                raw_frame = self.fix_raw_frame(short_buf)
                return ax25frame.Frame.from_bytes(raw_frame)
            except OSError as e:
                # A TCP reset is an OSError. Leaving it unhandled spins
                # this loop: select() stays readable and recv() raises
                # again. BlockingIOError is "no data" and falls through.
                if self._socket_is_dead(e):
                    LOG.warning(f'KISS read failed ({e})')
                    self._read_lost(e)
                    continue
                if 'Resource temporarily unavailable' in str(e):
                    if not blocking:
                        if len(short_buf) == 0:
                            break
            except aprslib.ConnectionDrop:
                self._read_lost()
                continue
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
