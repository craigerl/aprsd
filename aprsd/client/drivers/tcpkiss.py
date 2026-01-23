"""
APRSD KISS Client Driver using native KISS implementation.

This module provides a KISS client driver for APRSD using the new
non-asyncio KISSInterface implementation.
"""

import datetime
import logging
import select
import socket
from typing import Any, Dict

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
        self.keepalive = datetime.datetime.now()
        # This is initialized in setup_connection()
        self.socket = None

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

    def close(self):
        """Close the connection."""
        self._connected = False
        if self.socket:
            try:
                self.socket.close()
            except Exception as e:
                LOG.error(f'close: error closing socket: {e}')
                pass
        else:
            LOG.warning('close: socket not initialized. no reason to close.')

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
        return True

    def setup_connection(self):
        """Set up the KISS interface."""
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

    def stats(self, serializable: bool = False) -> Dict[str, Any]:
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
