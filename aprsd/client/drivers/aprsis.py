import datetime
import logging
import time
from typing import Callable

from aprslib.exceptions import LoginError
from loguru import logger
from oslo_config import cfg

from aprsd import client, exception
from aprsd.client.drivers.lib.aprslib import APRSLibClient
from aprsd.packets import core

CONF = cfg.CONF
LOG = logging.getLogger('APRSD')
LOGU = logger


# class APRSISDriver(metaclass=trace.TraceWrapperMetaclass):
class APRSISDriver:
    """This is the APRS-IS driver for the APRSD client.

    This driver uses our modified aprslib.IS class to connect to the APRS-IS server.

    """

    _client = None
    _checks = False

    def __init__(self):
        max_timeout = {'hours': 0.0, 'minutes': 2, 'seconds': 0}
        self.max_delta = datetime.timedelta(**max_timeout)
        self.login_status = {
            'success': False,
            'message': None,
        }

    @staticmethod
    def is_enabled():
        # Defaults to True if the enabled flag is non existent
        try:
            return CONF.aprs_network.enabled
        except KeyError:
            return False

    @staticmethod
    def is_configured():
        if APRSISDriver.is_enabled():
            # Ensure that the config vars are correctly set
            if not CONF.aprs_network.login:
                LOG.error('Config aprs_network.login not set.')
                raise exception.MissingConfigOptionException(
                    'aprs_network.login is not set.',
                )
            if not CONF.aprs_network.password:
                LOG.error('Config aprs_network.password not set.')
                raise exception.MissingConfigOptionException(
                    'aprs_network.password is not set.',
                )
            if not CONF.aprs_network.host:
                LOG.error('Config aprs_network.host not set.')
                raise exception.MissingConfigOptionException(
                    'aprs_network.host is not set.',
                )

            return True
        return True

    @property
    def is_alive(self):
        if not self._client:
            LOG.warning(f'APRS_CLIENT {self._client} alive? NO!!!')
            return False
        return self._client.is_alive() and not self._is_stale_connection()

    def close(self):
        if self._client:
            self._client.stop()
            self._client.close()

    def send(self, packet: core.Packet) -> bool:
        return self._client.send(packet)

    def setup_connection(self):
        user = CONF.aprs_network.login
        password = CONF.aprs_network.password
        host = CONF.aprs_network.host
        port = CONF.aprs_network.port
        self.connected = False
        backoff = 1
        retries = 3
        retry_count = 0
        while not self.connected:
            retry_count += 1
            if retry_count >= retries:
                break
            try:
                LOG.info(
                    f'Creating aprslib client({host}:{port}) and logging in {user}.'
                )
                self._client = APRSLibClient(
                    user, passwd=password, host=host, port=port
                )
                # Force the log to be the same
                self._client.logger = LOG
                self._client.connect()
                self.connected = self.login_status['success'] = True
                self.login_status['message'] = self._client.server_string
                backoff = 1
            except LoginError as e:
                LOG.error(f"Failed to login to APRS-IS Server '{e}'")
                self.connected = self.login_status['success'] = False
                self.login_status['message'] = (
                    e.message if hasattr(e, 'message') else str(e)
                )
                LOG.error(self.login_status['message'])
                time.sleep(backoff)
            except Exception as e:
                LOG.error(f"Unable to connect to APRS-IS server. '{e}' ")
                self.connected = self.login_status['success'] = False
                self.login_status['message'] = getattr(e, 'message', str(e))
                time.sleep(backoff)
                # Don't allow the backoff to go to inifinity.
                if backoff > 5:
                    backoff = 5
                else:
                    backoff += 1
                continue

    def set_filter(self, filter):
        self._client.set_filter(filter)

    def login_success(self) -> bool:
        return self.login_status.get('success', False)

    def login_failure(self) -> str:
        return self.login_status.get('message', None)

    @property
    def filter(self):
        return self._client.filter

    @property
    def server_string(self):
        return self._client.server_string

    @property
    def keepalive(self):
        return self._client.aprsd_keepalive

    def _is_stale_connection(self):
        delta = datetime.datetime.now() - self._client.aprsd_keepalive
        if delta > self.max_delta:
            LOG.error(f'Connection is stale, last heard {delta} ago.')
            return True
        return False

    @staticmethod
    def transport():
        return client.TRANSPORT_APRSIS

    def decode_packet(self, *args, **kwargs):
        """APRS lib already decodes this."""
        return core.factory(args[0])

    def consumer(self, callback: Callable, raw: bool = False):
        if self._client:
            try:
                self._client.consumer(
                    callback,
                    blocking=False,
                    immortal=False,
                    raw=raw,
                )
            except Exception as e:
                LOG.error(e)
                LOG.info(e.__cause__)
                raise e
        else:
            LOG.warning('client is None, might be resetting.')
            self.connected = False

    def stats(self, serializable=False) -> dict:
        stats = {}
        if self.is_configured():
            if self._client:
                keepalive = self._client.aprsd_keepalive
                server_string = self._client.server_string
                if serializable:
                    keepalive = keepalive.isoformat()
                filter = self.filter
            else:
                keepalive = 'None'
                server_string = 'None'
                filter = 'None'
            stats = {
                'connected': self.is_alive,
                'filter': filter,
                'login_status': self.login_status,
                'connection_keepalive': keepalive,
                'server_string': server_string,
                'transport': self.transport(),
            }

        return stats
