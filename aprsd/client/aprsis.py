import datetime
import logging
import time

from aprslib.exceptions import LoginError
from oslo_config import cfg

from aprsd import client, exception
from aprsd.client import base
from aprsd.client.drivers import aprsis
from aprsd.packets import core


CONF = cfg.CONF
LOG = logging.getLogger("APRSD")


class APRSISClient(base.APRSClient):

    _client = None

    def __init__(self):
        max_timeout = {"hours": 0.0, "minutes": 2, "seconds": 0}
        self.max_delta = datetime.timedelta(**max_timeout)

    def stats(self) -> dict:
        stats = {}
        if self.is_configured():
            stats = {
                "server_string": self._client.server_string,
                "sever_keepalive": self._client.aprsd_keepalive,
                "filter": self.filter,
            }

        return stats

    @staticmethod
    def is_enabled():
        # Defaults to True if the enabled flag is non existent
        try:
            return CONF.aprs_network.enabled
        except KeyError:
            return False

    @staticmethod
    def is_configured():
        if APRSISClient.is_enabled():
            # Ensure that the config vars are correctly set
            if not CONF.aprs_network.login:
                LOG.error("Config aprs_network.login not set.")
                raise exception.MissingConfigOptionException(
                    "aprs_network.login is not set.",
                )
            if not CONF.aprs_network.password:
                LOG.error("Config aprs_network.password not set.")
                raise exception.MissingConfigOptionException(
                    "aprs_network.password is not set.",
                )
            if not CONF.aprs_network.host:
                LOG.error("Config aprs_network.host not set.")
                raise exception.MissingConfigOptionException(
                    "aprs_network.host is not set.",
                )

            return True
        return True

    def _is_stale_connection(self):
        delta = datetime.datetime.now() - self._client.aprsd_keepalive
        if delta > self.max_delta:
            LOG.error(f"Connection is stale, last heard {delta} ago.")
            return True

    def is_alive(self):
        if self._client:
            return self._client.is_alive() and not self._is_stale_connection()
        else:
            LOG.warning(f"APRS_CLIENT {self._client} alive? NO!!!")
            return False

    def close(self):
        if self._client:
            self._client.stop()
            self._client.close()

    @staticmethod
    def transport():
        return client.TRANSPORT_APRSIS

    def decode_packet(self, *args, **kwargs):
        """APRS lib already decodes this."""
        return core.factory(args[0])

    def setup_connection(self):
        user = CONF.aprs_network.login
        password = CONF.aprs_network.password
        host = CONF.aprs_network.host
        port = CONF.aprs_network.port
        self.connected = False
        backoff = 1
        aprs_client = None
        while not self.connected:
            try:
                LOG.info(f"Creating aprslib client({host}:{port}) and logging in {user}.")
                aprs_client = aprsis.Aprsdis(user, passwd=password, host=host, port=port)
                # Force the log to be the same
                aprs_client.logger = LOG
                aprs_client.connect()
                self.connected = True
                backoff = 1
            except LoginError as e:
                LOG.error(f"Failed to login to APRS-IS Server '{e}'")
                self.connected = False
                time.sleep(backoff)
            except Exception as e:
                LOG.error(f"Unable to connect to APRS-IS server. '{e}' ")
                self.connected = False
                time.sleep(backoff)
                # Don't allow the backoff to go to inifinity.
                if backoff > 5:
                    backoff = 5
                else:
                    backoff += 1
                continue
        self._client = aprs_client
        return aprs_client

    def consumer(self, callback, blocking=False, immortal=False, raw=False):
        self._client.consumer(
            callback, blocking=blocking,
            immortal=immortal, raw=raw,
        )
