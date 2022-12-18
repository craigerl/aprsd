import datetime
import logging
import time
import tracemalloc

from aprsd import client, packets, stats, utils
from aprsd.threads import APRSDThread, APRSDThreadList


LOG = logging.getLogger("APRSD")


class KeepAliveThread(APRSDThread):
    cntr = 0
    checker_time = datetime.datetime.now()

    def __init__(self, config):
        tracemalloc.start()
        super().__init__("KeepAlive")
        self.config = config
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

            try:
                login = self.config["aprsd"]["callsign"]
            except KeyError:
                login = self.config["ham"]["callsign"]

            if pkt_tracker.is_initialized():
                tracked_packets = len(pkt_tracker)
            else:
                tracked_packets = 0

            keepalive = (
                "{} - Uptime {} RX:{} TX:{} Tracker:{} Msgs TX:{} RX:{} "
                "Last:{} Email: {} - RAM Current:{} Peak:{} Threads:{}"
            ).format(
                login,
                utils.strfdelta(stats_obj.uptime),
                pl.total_recv,
                pl.total_tx,
                tracked_packets,
                stats_obj.msgs_tx,
                stats_obj.msgs_rx,
                last_msg_time,
                email_thread_time,
                utils.human_size(current),
                utils.human_size(peak),
                len(thread_list),
            )
            LOG.info(keepalive)

            # See if we should reset the aprs-is client
            # Due to losing a keepalive from them
            delta_dict = utils.parse_delta_str(last_msg_time)
            delta = datetime.timedelta(**delta_dict)

            if delta > self.max_delta:
                #  We haven't gotten a keepalive from aprs-is in a while
                # reset the connection.a
                if not client.KISSClient.is_enabled(self.config):
                    LOG.warning(f"Resetting connection to APRS-IS {delta}")
                    client.factory.create().reset()

            # Check version every hour
            delta = now - self.checker_time
            if delta > datetime.timedelta(hours=1):
                self.checker_time = now
                level, msg = utils._check_version()
                if level:
                    LOG.warning(msg)
        self.cntr += 1
        time.sleep(1)
        return True
