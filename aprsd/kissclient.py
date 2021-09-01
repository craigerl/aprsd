import asyncio
import logging

from aioax25 import interface
from aioax25 import kiss as kiss
from aioax25.aprs import APRSInterface

from aprsd import trace


TRANSPORT_TCPKISS = "tcpkiss"
TRANSPORT_SERIALKISS = "serialkiss"
LOG = logging.getLogger("APRSD")


class KISSClient:

    _instance = None
    config = None
    ax25client = None
    loop = None

    def __new__(cls, *args, **kwargs):
        """Singleton for this class."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            # initialize shit here
        return cls._instance

    def __init__(self, config=None):
        if config:
            self.config = config

    @staticmethod
    def kiss_enabled(config):
        """Return if tcp or serial KISS is enabled."""
        if "kiss" not in config:
            return False

        if "serial" in config["kiss"]:
            if config["kiss"]["serial"].get("enabled", False):
                return True

        if "tcp" in config["kiss"]:
            if config["kiss"]["tcp"].get("enabled", False):
                return True

    @staticmethod
    def transport(config):
        if "serial" in config["kiss"]:
            if config["kiss"]["serial"].get("enabled", False):
                return TRANSPORT_SERIALKISS

        if "tcp" in config["kiss"]:
            if config["kiss"]["tcp"].get("enabled", False):
                return TRANSPORT_TCPKISS

    @property
    def client(self):
        if not self.ax25client:
            self.ax25client = self.setup_connection()
        return self.ax25client

    def reset(self):
        """Call this to fore a rebuild/reconnect."""
        self.ax25client.stop()
        del self.ax25client

    @trace.trace
    def setup_connection(self):
        ax25client = Aioax25Client(self.config)
        LOG.debug("Complete")
        return ax25client


class Aioax25Client:
    def __init__(self, config):
        self.config = config
        self.setup()

    def setup(self):
        # we can be TCP kiss or Serial kiss

        self.loop = asyncio.get_event_loop()
        if "serial" in self.config["kiss"] and self.config["kiss"]["serial"].get(
            "enabled",
            False,
        ):
            LOG.debug(
                "Setting up Serial KISS connection to {}".format(
                    self.config["kiss"]["serial"]["device"],
                ),
            )
            self.kissdev = kiss.SerialKISSDevice(
                device=self.config["kiss"]["serial"]["device"],
                baudrate=self.config["kiss"]["serial"].get("baudrate", 9600),
                loop=self.loop,
            )
        elif "tcp" in self.config["kiss"] and self.config["kiss"]["tcp"].get(
            "enabled",
            False,
        ):
            LOG.debug(
                "Setting up KISSTCP Connection to {}:{}".format(
                    self.config["kiss"]["tcp"]["host"],
                    self.config["kiss"]["tcp"]["port"],
                ),
            )
            self.kissdev = kiss.TCPKISSDevice(
                self.config["kiss"]["tcp"]["host"],
                self.config["kiss"]["tcp"]["port"],
                loop=self.loop,
                log=LOG,
            )

        self.kissdev.open()
        self.kissport0 = self.kissdev[0]

        LOG.debug("Creating AX25Interface")
        self.ax25int = interface.AX25Interface(kissport=self.kissport0, loop=self.loop)

        LOG.debug("Creating APRSInterface")
        self.aprsint = APRSInterface(
            ax25int=self.ax25int,
            mycall=self.config["kiss"]["callsign"],
            log=LOG,
        )

    def stop(self):
        LOG.debug(self.kissdev)
        self.kissdev._close()
        self.loop.stop()

    def consumer(self, callback, callsign=None):
        if not callsign:
            callsign = self.config["ham"]["callsign"]
        self.aprsint.bind(callback=callback, callsign="WB4BOR", ssid=12, regex=False)

    def send(self, msg):
        """Send an APRS Message object."""
        payload = f"{msg._filter_for_send()}"
        self.aprsint.send_message(
            addressee=msg.tocall,
            message=payload,
            path=["WIDE1-1", "WIDE2-1"],
            oneshot=True,
        )


def get_client():
    cl = KISSClient()
    return cl.client
