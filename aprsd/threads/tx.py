import logging
import time

from oslo_config import cfg
from rush import quota, throttle
from rush.contrib import decorator
from rush.limiters import periodic
from rush.stores import dictionary

from aprsd import client
from aprsd import conf  # noqa
from aprsd import threads as aprsd_threads
from aprsd.packets import core, tracker


CONF = cfg.CONF
LOG = logging.getLogger("APRSD")

msg_t = throttle.Throttle(
    limiter=periodic.PeriodicLimiter(
        store=dictionary.DictionaryStore(),
    ),
    rate=quota.Quota.per_second(
        count=CONF.msg_rate_limit_period,
    ),
)
ack_t = throttle.Throttle(
    limiter=periodic.PeriodicLimiter(
        store=dictionary.DictionaryStore(),
    ),
    rate=quota.Quota.per_second(
        count=CONF.ack_rate_limit_period,
    ),
)

msg_throttle_decorator = decorator.ThrottleDecorator(throttle=msg_t)
ack_throttle_decorator = decorator.ThrottleDecorator(throttle=ack_t)


@msg_throttle_decorator.sleep_and_retry
def send(packet: core.Packet, direct=False, aprs_client=None):
    """Send a packet either in a thread or directly to the client."""
    # prepare the packet for sending.
    # This constructs the packet.raw
    packet.prepare()
    if isinstance(packet, core.AckPacket):
        _send_ack(packet, direct=direct, aprs_client=aprs_client)
    else:
        _send_packet(packet, direct=direct, aprs_client=aprs_client)


@msg_throttle_decorator.sleep_and_retry
def _send_packet(packet: core.Packet, direct=False, aprs_client=None):
    if not direct:
        thread = SendPacketThread(packet=packet)
        thread.start()
    else:
        _send_direct(packet, aprs_client=aprs_client)


@ack_throttle_decorator.sleep_and_retry
def _send_ack(packet: core.AckPacket, direct=False, aprs_client=None):
    if not direct:
        thread = SendAckThread(packet=packet)
        thread.start()
    else:
        _send_direct(packet, aprs_client=aprs_client)


def _send_direct(packet, aprs_client=None):
    if aprs_client:
        cl = aprs_client
    else:
        cl = client.factory.create()

    packet.update_timestamp()
    packet.log(header="TX")
    cl.send(packet)


class SendPacketThread(aprsd_threads.APRSDThread):
    loop_count: int = 1

    def __init__(self, packet):
        self.packet = packet
        name = self.packet.raw[:5]
        super().__init__(f"TXPKT-{self.packet.msgNo}-{name}")
        pkt_tracker = tracker.PacketTrack()
        pkt_tracker.add(packet)

    def loop(self):
        """Loop until a message is acked or it gets delayed.

        We only sleep for 5 seconds between each loop run, so
        that CTRL-C can exit the app in a short period.  Each sleep
        means the app quitting is blocked until sleep is done.
        So we keep track of the last send attempt and only send if the
        last send attempt is old enough.

        """
        pkt_tracker = tracker.PacketTrack()
        # lets see if the message is still in the tracking queue
        packet = pkt_tracker.get(self.packet.msgNo)
        if not packet:
            # The message has been removed from the tracking queue
            # So it got acked and we are done.
            LOG.info(
                f"{self.packet.__class__.__name__}"
                f"({self.packet.msgNo}) "
                "Message Send Complete via Ack.",
            )
            return False
        else:
            send_now = False
            if packet.send_count == packet.retry_count:
                # we reached the send limit, don't send again
                # TODO(hemna) - Need to put this in a delayed queue?
                LOG.info(
                    f"{packet.__class__.__name__} "
                    f"({packet.msgNo}) "
                    "Message Send Complete. Max attempts reached"
                    f" {packet.retry_count}",
                )
                if not packet.allow_delay:
                    pkt_tracker.remove(packet.msgNo)
                return False

            # Message is still outstanding and needs to be acked.
            if packet.last_send_time:
                # Message has a last send time tracking
                now = int(round(time.time()))
                sleeptime = (packet.send_count + 1) * 31
                delta = now - packet.last_send_time
                if delta > sleeptime:
                    # It's time to try to send it again
                    send_now = True
            else:
                send_now = True

            if send_now:
                # no attempt time, so lets send it, and start
                # tracking the time.
                packet.last_send_time = int(round(time.time()))
                send(packet, direct=True)
                packet.send_count += 1

            time.sleep(1)
            # Make sure we get called again.
            self.loop_count += 1
            return True


class SendAckThread(aprsd_threads.APRSDThread):
    loop_count: int = 1

    def __init__(self, packet):
        self.packet = packet
        super().__init__(f"SendAck-{self.packet.msgNo}")

    def loop(self):
        """Separate thread to send acks with retries."""
        send_now = False
        if self.packet.send_count == self.packet.retry_count:
            # we reached the send limit, don't send again
            # TODO(hemna) - Need to put this in a delayed queue?
            LOG.info(
                f"{self.packet.__class__.__name__}"
                f"({self.packet.msgNo}) "
                "Send Complete. Max attempts reached"
                f" {self.packet.retry_count}",
            )
            return False

        if self.packet.last_send_time:
            # Message has a last send time tracking
            now = int(round(time.time()))

            # aprs duplicate detection is 30 secs?
            # (21 only sends first, 28 skips middle)
            sleep_time = 31
            delta = now - self.packet.last_send_time
            if delta > sleep_time:
                # It's time to try to send it again
                send_now = True
            elif self.loop_count % 10 == 0:
                LOG.debug(f"Still wating. {delta}")
        else:
            send_now = True

        if send_now:
            send(self.packet, direct=True)
            self.packet.send_count += 1
            self.packet.last_send_time = int(round(time.time()))

        time.sleep(1)
        self.loop_count += 1
        return True


class BeaconSendThread(aprsd_threads.APRSDThread):
    """Thread that sends a GPS beacon packet periodically.

    Settings are in the [DEFAULT] section of the config file.
    """
    _loop_cnt: int = 1

    def __init__(self):
        super().__init__("BeaconSendThread")
        self._loop_cnt = 1
        # Make sure Latitude and Longitude are set.
        if not CONF.latitude or not CONF.longitude:
            LOG.error(
                "Latitude and Longitude are not set in the config file."
                "Beacon will not be sent and thread is STOPPED.",
            )
            self.stop()
        LOG.info(
            "Beacon thread is running and will send "
            f"beacons every {CONF.beacon_interval} seconds.",
        )

    def loop(self):
        # Only dump out the stats every N seconds
        if self._loop_cnt % CONF.beacon_interval == 0:
            pkt = core.BeaconPacket(
                from_call=CONF.callsign,
                to_call="APRS",
                latitude=float(CONF.latitude),
                longitude=float(CONF.longitude),
                comment="APRSD GPS Beacon",
                symbol=CONF.beacon_symbol,
            )
            send(pkt, direct=True)
        self._loop_cnt += 1
        time.sleep(1)
        return True
