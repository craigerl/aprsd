import logging
import select
import time

import aprslib

LOG = logging.getLogger("APRSD")


class Client:
    """Singleton client class that constructs the aprslib connection."""

    _instance = None
    aprs_client = None
    config = None

    def __new__(cls, *args, **kwargs):
        """This magic turns this into a singleton."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
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
                aprs_client = Aprsdis(user, passwd=password, host=host, port=port)
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


class Aprsdis(aprslib.IS):
    """Extend the aprslib class so we can exit properly."""

    # flag to tell us to stop
    thread_stop = False

    # timeout in seconds
    select_timeout = 10

    def stop(self):
        self.thread_stop = True
        LOG.info("Shutdown Aprsdis client.")

    def _socket_readlines(self, blocking=False):
        """
        Generator for complete lines, received from the server
        """
        try:
            self.sock.setblocking(0)
        except OSError as e:
            self.logger.error("socket error when setblocking(0): %s" % str(e))
            raise aprslib.ConnectionDrop("connection dropped")

        while not self.thread_stop:
            short_buf = b""
            newline = b"\r\n"

            # set a select timeout, so we get a chance to exit
            # when user hits CTRL-C
            readable, writable, exceptional = select.select(
                [self.sock],
                [],
                [],
                self.select_timeout,
            )
            if not readable:
                continue

            try:
                short_buf = self.sock.recv(4096)

                # sock.recv returns empty if the connection drops
                if not short_buf:
                    self.logger.error("socket.recv(): returned empty")
                    raise aprslib.ConnectionDrop("connection dropped")
            except OSError as e:
                # self.logger.error("socket error on recv(): %s" % str(e))
                if "Resource temporarily unavailable" in str(e):
                    if not blocking:
                        if len(self.buf) == 0:
                            break

            self.buf += short_buf

            while newline in self.buf:
                line, self.buf = self.buf.split(newline, 1)

                yield line


def get_client():
    cl = Client()
    return cl.client
