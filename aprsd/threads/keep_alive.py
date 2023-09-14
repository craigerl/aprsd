import datetime
import logging
import time
import tracemalloc

from oslo_config import cfg

from aprsd import client, packets, stats, utils
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
        if self.cntr % 60 == 0:
            pkt_tracker = packets.PacketTrack()
            stats_obj = stats.APRSDStats()
            pl = packets.PacketList()
            thread_list = APRSDThreadList()
            now = datetime.datetime.now()
            last_email = stats_obj.email_thread_time
            if last_email:
                email_thread_time = utils.strfdelta(now - last_email)
            else:
                email_thread_time = "N/A"

            last_msg_time = utils.strfdelta(now - stats_obj.aprsis_keepalive)

            current, peak = tracemalloc.get_traced_memory()
            stats_obj.set_memory(current)
            stats_obj.set_memory_peak(peak)

            login = CONF.callsign

            tracked_packets = len(pkt_tracker)

            keepalive = (
                "{} - Uptime {} RX:{} TX:{} Tracker:{} Msgs TX:{} RX:{} "
                "Last:{} Email: {} - RAM Current:{} Peak:{} Threads:{}"
            ).format(
                login,
                utils.strfdelta(stats_obj.uptime),
                pl.total_rx(),
                pl.total_tx(),
                tracked_packets,
                stats_obj._pkt_cnt["MessagePacket"]["tx"],
                stats_obj._pkt_cnt["MessagePacket"]["rx"],
                last_msg_time,
                email_thread_time,
                utils.human_size(current),
                utils.human_size(peak),
                len(thread_list),
            )
            LOG.info(keepalive)
            thread_out = []
            thread_info = {}
            for thread in thread_list.threads_list:
                alive = thread.is_alive()
                age = thread.loop_age()
                key = thread.__class__.__name__
                thread_out.append(f"{key}:{alive}:{age}")
                if key not in thread_info:
                    thread_info[key] = {}
                thread_info[key]["alive"] = alive
                thread_info[key]["age"] = age
                if not alive:
                    LOG.error(f"Thread {thread}")
            LOG.info(",".join(thread_out))
            stats_obj.set_thread_info(thread_info)

            # check the APRS connection
            cl = client.factory.create()
            # Reset the connection if it's dead and this isn't our
            # First time through the loop.
            # The first time through the loop can happen at startup where
            # The keepalive thread starts before the client has a chance
            # to make it's connection the first time.
            if not cl.is_alive() and self.cntr > 0:
                LOG.error(f"{cl.__class__.__name__} is not alive!!! Resetting")
                client.factory.create().reset()
            else:
                # See if we should reset the aprs-is client
                # Due to losing a keepalive from them
                delta_dict = utils.parse_delta_str(last_msg_time)
                delta = datetime.timedelta(**delta_dict)

                if delta > self.max_delta:
                    #  We haven't gotten a keepalive from aprs-is in a while
                    # reset the connection.a
                    if not client.KISSClient.is_enabled():
                        LOG.warning(f"Resetting connection to APRS-IS {delta}")
                        client.factory.create().reset()

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
