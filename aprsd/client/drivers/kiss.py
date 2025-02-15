import datetime
import logging

import kiss
from ax253 import Frame
from oslo_config import cfg

from aprsd import conf  # noqa
from aprsd.packets import core
from aprsd.utils import trace

CONF = cfg.CONF
LOG = logging.getLogger('APRSD')


class KISS3Client:
    path = []

    # date for last time we heard from the server
    aprsd_keepalive = datetime.datetime.now()
    _connected = False

    def __init__(self):
        self.setup()

    def is_alive(self):
        return self._connected

    def setup(self):
        # we can be TCP kiss or Serial kiss
        if CONF.kiss_serial.enabled:
            LOG.debug(
                'KISS({}) Serial connection to {}'.format(
                    kiss.__version__,
                    CONF.kiss_serial.device,
                ),
            )
            self.kiss = kiss.SerialKISS(
                port=CONF.kiss_serial.device,
                speed=CONF.kiss_serial.baudrate,
                strip_df_start=True,
            )
            self.path = CONF.kiss_serial.path
        elif CONF.kiss_tcp.enabled:
            LOG.debug(
                'KISS({}) TCP Connection to {}:{}'.format(
                    kiss.__version__,
                    CONF.kiss_tcp.host,
                    CONF.kiss_tcp.port,
                ),
            )
            self.kiss = kiss.TCPKISS(
                host=CONF.kiss_tcp.host,
                port=CONF.kiss_tcp.port,
                strip_df_start=True,
            )
            self.path = CONF.kiss_tcp.path

        LOG.debug('Starting KISS interface connection')
        try:
            self.kiss.start()
            if self.kiss.protocol.transport.is_closing():
                LOG.warning('KISS transport is closing, not setting consumer callback')
                self._connected = False
            else:
                self._connected = True
        except Exception:
            LOG.error('Failed to start KISS interface.')
            self._connected = False

    @trace.trace
    def stop(self):
        if not self._connected:
            # do nothing since we aren't connected
            return

        try:
            self.kiss.stop()
            self.kiss.loop.call_soon_threadsafe(
                self.kiss.protocol.transport.close,
            )
        except Exception:
            LOG.error('Failed to stop KISS interface.')

    def close(self):
        self.stop()

    def set_filter(self, filter):
        # This does nothing right now.
        pass

    def parse_frame(self, frame_bytes):
        try:
            frame = Frame.from_bytes(frame_bytes)
            # Now parse it with aprslib
            kwargs = {
                'frame': frame,
            }
            self._parse_callback(**kwargs)
            self.aprsd_keepalive = datetime.datetime.now()
        except Exception as ex:
            LOG.error('Failed to parse bytes received from KISS interface.')
            LOG.exception(ex)

    def consumer(self, callback):
        if not self._connected:
            raise Exception('KISS transport is not connected')

        self._parse_callback = callback
        if not self.kiss.protocol.transport.is_closing():
            self.kiss.read(callback=self.parse_frame, min_frames=1)
        else:
            self._connected = False

    def send(self, packet):
        """Send an APRS Message object."""

        payload = None
        path = self.path
        if isinstance(packet, core.Packet):
            packet.prepare()
            payload = packet.payload.encode('US-ASCII')
            if packet.path:
                path = packet.path
        else:
            msg_payload = f'{packet.raw}{{{str(packet.msgNo)}'
            payload = (
                ':{:<9}:{}'.format(
                    packet.to_call,
                    msg_payload,
                )
            ).encode('US-ASCII')

        LOG.debug(
            f"KISS Send '{payload}' TO '{packet.to_call}' From "
            f"'{packet.from_call}' with PATH '{path}'",
        )
        frame = Frame.ui(
            destination='APZ100',
            source=packet.from_call,
            path=path,
            info=payload,
        )
        self.kiss.write(frame)
