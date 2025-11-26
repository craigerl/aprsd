"""
APRSD KISS Client Driver using native KISS implementation.

This module provides a KISS client driver for APRSD using the new
non-asyncio KISSInterface implementation.
"""

import datetime
import logging
import select
from typing import Any, Dict

import serial
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


class SerialKISSDriver(KISSDriver):
    """APRSD client driver for Serial KISS connections."""

    _instance = None

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

    @property
    def transport(self) -> str:
        return client.TRANSPORT_SERIALKISS

    @staticmethod
    def is_enabled() -> bool:
        """Check if KISS is enabled in configuration.

        Returns:
            bool: True if either Serial is enabled
        """
        return CONF.kiss_serial.enabled

    @staticmethod
    def is_configured():
        # Ensure that the config vars are correctly set
        if SerialKISSDriver.is_enabled():
            if not CONF.kiss_serial.device:
                LOG.error('KISS Serial enabled, but no device is set.')
                raise exception.MissingConfigOptionException(
                    'kiss_serial.device is not set.',
                )
            return True
        return False

    def close(self):
        """Close the connection."""
        self._connected = False

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
                    f'Serial KISS Connection to {CONF.kiss_serial.device}:{CONF.kiss_serial.baudrate}'
                )
                self.path = CONF.kiss_serial.path
                self.connect()
            if self._connected:
                LOG.info('KISS interface initialized')
            else:
                LOG.error('Failed to connect to KISS interface')
        except Exception as ex:
            LOG.error('Failed to initialize KISS interface')
            LOG.exception(ex)
            self._connected = False

    def connect(self):
        """Connect to the KISS interface."""
        if not self.is_enabled():
            LOG.error('KISS is not enabled in configuration')
            return

        if self._connected:
            LOG.warning('KISS interface already connected')
            return

        try:
            self.socket = serial.Serial(
                CONF.kiss_serial.device, CONF.kiss_serial.baudrate
            )
            self.socket.open()
            self._connected = True
        except serial.SerialException as e:
            LOG.error(f'Failed to connect to KISS interface: {e}')
            self._connected = False
            return False
        except Exception as ex:
            LOG.error('Failed to connect to KISS interface')
            LOG.exception(ex)
            self._connected = False

    def read_frame(self):
        """Read a frame from the KISS interface."""
        if not self.socket:
            return None

        if not self._connected:
            return None

        while self._connected:
            try:
                readable, _, _ = select.select(
                    [self.socket],
                    [],
                    [],
                    self.select_timeout,
                )
                if not readable:
                    continue
            except Exception as e:
                # No need to log if we are not running.
                # this happens when the client is stopped/closed.
                LOG.error(f'Error in read loop: {e}')
                self._connected = False
                break

            try:
                short_buf = self.socket.read(1024)
                if not short_buf:
                    continue

                raw_frame = self.fix_raw_frame(short_buf)
                return ax25frame.Frame.from_bytes(raw_frame)
            except Exception as e:
                LOG.error(f'Error in read loop: {e}')
                self._connected = False
                break

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

    def stats(self, serializable: bool = False) -> Dict[str, Any]:
        """Get client statistics.

        Returns:
            Dict containing client statistics
        """
        stats = super().stats(serializable=serializable)
        stats['device'] = CONF.kiss_serial.device
        stats['baudrate'] = CONF.kiss_serial.baudrate
        return stats
