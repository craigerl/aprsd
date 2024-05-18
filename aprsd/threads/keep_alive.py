import datetime
import logging
import time
import tracemalloc

from oslo_config import cfg

from aprsd import packets, utils
from aprsd.client import client_factory
from aprsd.log import log as aprsd_log
from aprsd.stats import collector
from aprsd.threads import APRSDThread, APRSDThreadList


CONF = cfg.CONF
LOG = logging.getLogger("APRSD")


class KeepAliveThread(APRSDThread):
    cntr = 0
    checker_time = datetime.datetime.now()

    def __init__(self):
        tracemalloc.start()
        super().__init__("KeepAlive")
        max_timeout = {"hours": 0.0, "minutes": 2, "seconds": 0}
        self.max_delta = datetime.timedelta(**max_timeout)

    def loop(self):
        if self.loop_count % 60 == 0:
            stats_json = collector.Collector().collect()
            pl = packets.PacketList()
            thread_list = APRSDThreadList()
            now = datetime.datetime.now()

            if "EmailStats" in stats_json:
                email_stats = stats_json["EmailStats"]
                if email_stats.get("last_check_time"):
                    email_thread_time = utils.strfdelta(now - email_stats["last_check_time"])
                else:
                    email_thread_time = "N/A"
            else:
                email_thread_time = "N/A"

            if "APRSClientStats" in stats_json and stats_json["APRSClientStats"].get("transport") == "aprsis":
                if stats_json["APRSClientStats"].get("server_keepalive"):
                    last_msg_time = utils.strfdelta(now - stats_json["APRSClientStats"]["server_keepalive"])
                else:
                    last_msg_time = "N/A"
            else:
                last_msg_time = "N/A"

            tracked_packets = stats_json["PacketTrack"]["total_tracked"]
            tx_msg = 0
            rx_msg = 0
            if "PacketList" in stats_json:
                msg_packets = stats_json["PacketList"].get("MessagePacket")
                if msg_packets:
                    tx_msg = msg_packets.get("tx", 0)
                    rx_msg = msg_packets.get("rx", 0)

            keepalive = (
                "{} - Uptime {} RX:{} TX:{} Tracker:{} Msgs TX:{} RX:{} "
                "Last:{} Email: {} - RAM Current:{} Peak:{} Threads:{} LoggingQueue:{}"
            ).format(
                stats_json["APRSDStats"]["callsign"],
                stats_json["APRSDStats"]["uptime"],
                pl.total_rx(),
                pl.total_tx(),
                tracked_packets,
                tx_msg,
                rx_msg,
                last_msg_time,
                email_thread_time,
                stats_json["APRSDStats"]["memory_current_str"],
                stats_json["APRSDStats"]["memory_peak_str"],
                len(thread_list),
                aprsd_log.logging_queue.qsize(),
            )
            LOG.info(keepalive)
            if "APRSDThreadList" in stats_json:
                thread_list = stats_json["APRSDThreadList"]
                for thread_name in thread_list:
                    thread = thread_list[thread_name]
                    alive = thread["alive"]
                    age = thread["age"]
                    key = thread["name"]
                    if not alive:
                        LOG.error(f"Thread {thread}")
                    LOG.info(f"{key: <15} Alive? {str(alive): <5} {str(age): <20}")

            # check the APRS connection
            cl = client_factory.create()
            # Reset the connection if it's dead and this isn't our
            # First time through the loop.
            # The first time through the loop can happen at startup where
            # The keepalive thread starts before the client has a chance
            # to make it's connection the first time.
            if not cl.is_alive() and self.cntr > 0:
                LOG.error(f"{cl.__class__.__name__} is not alive!!! Resetting")
                client_factory.create().reset()
            # else:
            #     # See if we should reset the aprs-is client
            #     # Due to losing a keepalive from them
            #     delta_dict = utils.parse_delta_str(last_msg_time)
            #     delta = datetime.timedelta(**delta_dict)
            #
            #     if delta > self.max_delta:
            #         #  We haven't gotten a keepalive from aprs-is in a while
            #         # reset the connection.a
            #         if not client.KISSClient.is_enabled():
            #             LOG.warning(f"Resetting connection to APRS-IS {delta}")
            #             client.factory.create().reset()

            # Check version every day
            delta = now - self.checker_time
            if delta > datetime.timedelta(hours=24):
                self.checker_time = now
                level, msg = utils._check_version()
                if level:
                    LOG.warning(msg)
            self.cntr += 1
        time.sleep(1)
        return True
