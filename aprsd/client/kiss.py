import datetime
import logging

import aprslib
import timeago
from loguru import logger
from oslo_config import cfg

from aprsd import client, exception
from aprsd.client import base
from aprsd.client.drivers import kiss
from aprsd.packets import core

CONF = cfg.CONF
LOG = logging.getLogger('APRSD')
LOGU = logger


class KISSClient(base.APRSClient):
    _client = None
    keepalive = datetime.datetime.now()

    def stats(self, serializable=False) -> dict:
        stats = {}
        if self.is_configured():
            keepalive = self.keepalive
            if serializable:
                keepalive = keepalive.isoformat()
            stats = {
                'connected': self.is_connected,
                'connection_keepalive': keepalive,
                'transport': self.transport(),
            }
            if self.transport() == client.TRANSPORT_TCPKISS:
                stats['host'] = CONF.kiss_tcp.host
                stats['port'] = CONF.kiss_tcp.port
            elif self.transport() == client.TRANSPORT_SERIALKISS:
                stats['device'] = CONF.kiss_serial.device
        return stats

    @staticmethod
    def is_enabled():
        """Return if tcp or serial KISS is enabled."""
        if CONF.kiss_serial.enabled:
            return True

        if CONF.kiss_tcp.enabled:
            return True

        return False

    @staticmethod
    def is_configured():
        # Ensure that the config vars are correctly set
        if KISSClient.is_enabled():
            transport = KISSClient.transport()
            if transport == client.TRANSPORT_SERIALKISS:
                if not CONF.kiss_serial.device:
                    LOG.error('KISS serial enabled, but no device is set.')
                    raise exception.MissingConfigOptionException(
                        'kiss_serial.device is not set.',
                    )
            elif transport == client.TRANSPORT_TCPKISS:
                if not CONF.kiss_tcp.host:
                    LOG.error('KISS TCP enabled, but no host is set.')
                    raise exception.MissingConfigOptionException(
                        'kiss_tcp.host is not set.',
                    )

            return True
        return False

    def is_alive(self):
        if self._client:
            return self._client.is_alive()
        else:
            return False

    def close(self):
        if self._client:
            self._client.stop()

    def keepalive_check(self):
        # Don't check the first time through.
        if not self.is_alive() and self._checks:
            LOG.warning("Resetting client.  It's not alive.")
            self.reset()
        self._checks = True

    def keepalive_log(self):
        if ka := self._client.aprsd_keepalive:
            keepalive = timeago.format(ka)
        else:
            keepalive = 'N/A'
        LOGU.opt(colors=True).info(f'<green>Client keepalive {keepalive}</green>')

    @staticmethod
    def transport():
        if CONF.kiss_serial.enabled:
            return client.TRANSPORT_SERIALKISS

        if CONF.kiss_tcp.enabled:
            return client.TRANSPORT_TCPKISS

    def decode_packet(self, *args, **kwargs):
        """We get a frame, which has to be decoded."""
        LOG.debug(f'kwargs {kwargs}')
        frame = kwargs['frame']
        LOG.debug(f"Got an APRS Frame '{frame}'")
        # try and nuke the * from the fromcall sign.
        # frame.header._source._ch = False
        # payload = str(frame.payload.decode())
        # msg = f"{str(frame.header)}:{payload}"
        # msg = frame.tnc2
        # LOG.debug(f"Decoding {msg}")

        try:
            raw = aprslib.parse(str(frame))
            packet = core.factory(raw)
            if isinstance(packet, core.ThirdPartyPacket):
                return packet.subpacket
            else:
                return packet
        except Exception as ex:
            LOG.error(f'Error decoding packet: {ex}')

    def setup_connection(self):
        try:
            self._client = kiss.KISS3Client()
            self.connected = self.login_status['success'] = True
        except Exception as ex:
            self.connected = self.login_status['success'] = False
            self.login_status['message'] = str(ex)
        return self._client

    def consumer(self, callback, blocking=False, immortal=False, raw=False):
        try:
            self._client.consumer(callback)
            self.keepalive = datetime.datetime.now()
        except Exception as ex:
            LOG.error(f'Consumer failed {ex}')
            LOG.error(ex)
            raise ex
