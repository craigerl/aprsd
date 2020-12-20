import logging
import time

import aprslib

LOG = logging.getLogger("APRSD")


class Client(object):
    """Singleton client class that constructs the aprslib connection."""

    _instance = None
    aprs_client = None
    config = None

    def __new__(cls, *args, **kwargs):
        """This magic turns this into a singleton."""
        if cls._instance is None:
            cls._instance = super(Client, cls).__new__(cls)
            # Put any initialization here.
        return cls._instance

    def __init__(self, config=None):
        """Initialize the object instance."""
        if config:
            self.config = config

    @property
    def client(self):
        if not self.aprs_client:
            self.aprs_client = self.setup_connection()
        return self.aprs_client

    def reset(self):
        """Call this to force a rebuild/reconnect."""
        del self.aprs_client

    def setup_connection(self):
        user = self.config["aprs"]["login"]
        password = self.config["aprs"]["password"]
        host = self.config["aprs"].get("host", "rotate.aprs.net")
        port = self.config["aprs"].get("port", 14580)
        connected = False
        backoff = 1
        while not connected:
            try:
                LOG.info("Creating aprslib client")
                aprs_client = aprslib.IS(user, passwd=password, host=host, port=port)
                # Force the logging to be the same
                aprs_client.logger = LOG
                aprs_client.connect()
                connected = True
                backoff = 1
            except Exception as e:
                LOG.error("Unable to connect to APRS-IS server. '{}' ".format(e))
                time.sleep(backoff)
                backoff = backoff * 2
                continue
        LOG.debug("Logging in to APRS-IS with user '%s'" % user)
        return aprs_client


def get_client():
    cl = Client()
    return cl.client
