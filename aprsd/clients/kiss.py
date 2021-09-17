import asyncio
import logging

from aioax25 import interface
from aioax25 import kiss as kiss
from aioax25.aprs import APRSInterface


LOG = logging.getLogger("APRSD")


class Aioax25Client:
    def __init__(self, config):
        self.config = config
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self.loop = asyncio.get_event_loop()
        self.setup()

    def setup(self):
        # we can be TCP kiss or Serial kiss
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

    def set_filter(self, filter):
        # This does nothing right now.
        pass

    def consumer(self, callback, blocking=True, immortal=False, raw=False):
        callsign = self.config["kiss"]["callsign"]
        call = callsign.split("-")
        if len(call) > 1:
            callsign = call[0]
            ssid = int(call[1])
        else:
            ssid = 0
        self.aprsint.bind(callback=callback, callsign=callsign, ssid=ssid, regex=False)
        self.loop.run_forever()

    def send(self, msg):
        """Send an APRS Message object."""
        payload = f"{msg._filter_for_send()}"
        self.aprsint.send_message(
            addressee=msg.tocall,
            message=payload,
            path=["WIDE1-1", "WIDE2-1"],
            oneshot=True,
        )
