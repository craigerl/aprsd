import asyncio
import logging

from aioax25 import interface
from aioax25 import kiss as kiss
from aioax25.aprs import APRSInterface
from aioax25.aprs.frame import APRSFrame


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
                log=LOG,
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

        LOG.debug("Creating AX25Interface")
        self.ax25int = interface.AX25Interface(
            kissport=self.kissdev[0],
            loop=self.loop,
            log=LOG,
        )

        LOG.debug("Creating APRSInterface")
        self.aprsint = APRSInterface(
            ax25int=self.ax25int,
            mycall=self.config["aprsd"]["callsign"],
            log=LOG,
        )
        self.kissdev.open()

    def stop(self):
        LOG.debug(self.kissdev)
        self.loop.stop()
        self.kissdev.close()

    def set_filter(self, filter):
        # This does nothing right now.
        pass

    def consumer(self, callback, blocking=False, immortal=False, raw=False):
        callsign = self.config["aprsd"]["callsign"]
        call = callsign.split("-")
        if len(call) > 1:
            callsign = call[0]
            ssid = int(call[1])
        else:
            ssid = 0
        self.aprsint.bind(callback=callback, callsign=callsign, ssid=ssid, regex=False)

        # async def set_after(fut, delay, value):
        #     # Sleep for *delay* seconds.
        #     await asyncio.sleep(delay)
        #
        #     # Set *value* as a result of *fut* Future.
        #     fut.set_result(value)
        #
        # async def my_wait(fut):
        #     await fut
        #
        # fut = self.loop.create_future()
        # self.loop.create_task(
        #     set_after(fut, 5, "nothing")
        # )
        LOG.debug("RUN FOREVER")
        self.loop.run_forever()
        # my_wait(fut)

    def send(self, msg):
        """Send an APRS Message object."""

        # payload = (':%-9s:%s' % (
        #     msg.tocall,
        #     payload
        # )).encode('US-ASCII'),
        # payload = str(msg).encode('US-ASCII')
        msg_payload = f"{msg.message}{{{str(msg.id)}"
        payload = (
            ":{:<9}:{}".format(
                msg.tocall,
                msg_payload,
            )
        ).encode("US-ASCII")
        LOG.debug(f"Send '{payload}' TO KISS")

        self.aprsint.transmit(
            APRSFrame(
                destination=msg.tocall,
                source=msg.fromcall,
                payload=payload,
                repeaters=["WIDE1-1", "WIDE2-1"],
            ),
        )

        # self.aprsint.send_message(
        #     addressee=msg.tocall,
        #     message=payload,
        #     path=["WIDE1-1", "WIDE2-1"],
        #     oneshot=True,
        # )
