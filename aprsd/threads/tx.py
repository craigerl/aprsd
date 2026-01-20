import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import wrapt
from oslo_config import cfg
from rush import quota, throttle
from rush.contrib import decorator
from rush.limiters import periodic
from rush.stores import dictionary

from aprsd import conf  # noqa
from aprsd import threads as aprsd_threads
from aprsd.client.client import APRSDClient
from aprsd.packets import collector, core, tracker
from aprsd.packets import log as packet_log

CONF = cfg.CONF
LOG = logging.getLogger('APRSD')

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
s_lock = threading.Lock()

# Global scheduler instances (singletons)
_packet_scheduler = None
_ack_scheduler = None
_scheduler_lock = threading.Lock()


@wrapt.synchronized(s_lock)
@msg_throttle_decorator.sleep_and_retry
def send(packet: core.Packet, direct=False, aprs_client=None):
    """Send a packet either in a thread or directly to the client."""
    # prepare the packet for sending.
    # This constructs the packet.raw
    packet.prepare(create_msg_number=True)
    # Have to call the collector to track the packet
    # After prepare, as prepare assigns the msgNo
    collector.PacketCollector().tx(packet)
    if isinstance(packet, core.AckPacket):
        if CONF.enable_sending_ack_packets:
            _send_ack(packet, direct=direct, aprs_client=aprs_client)
        else:
            LOG.info('Sending ack packets is disabled. Not sending AckPacket.')
    else:
        _send_packet(packet, direct=direct, aprs_client=aprs_client)


@msg_throttle_decorator.sleep_and_retry
def _send_packet(packet: core.Packet, direct=False, aprs_client=None):
    if not direct:
        # Use threadpool scheduler instead of creating individual threads
        scheduler = _get_packet_scheduler()
        if scheduler and scheduler.is_alive():
            # Scheduler will handle the packet
            pass
        else:
            # Fallback to old method if scheduler not available
            thread = SendPacketThread(packet=packet)
            thread.start()
    else:
        _send_direct(packet, aprs_client=aprs_client)


@ack_throttle_decorator.sleep_and_retry
def _send_ack(packet: core.AckPacket, direct=False, aprs_client=None):
    if not direct:
        # Use threadpool scheduler instead of creating individual threads
        scheduler = _get_ack_scheduler()
        if scheduler and scheduler.is_alive():
            # Scheduler will handle the packet
            pass
        else:
            # Fallback to old method if scheduler not available
            thread = SendAckThread(packet=packet)
            thread.start()
    else:
        _send_direct(packet, aprs_client=aprs_client)


@msg_throttle_decorator.sleep_and_retry
def _send_direct(packet, aprs_client=None):
    if aprs_client:
        cl = aprs_client
    else:
        cl = APRSDClient()

    packet_log.log(packet, tx=True)
    try:
        cl.send(packet)
    except Exception as e:
        LOG.error(f'Failed to send packet: {packet}')
        LOG.error(e)
        return False
    else:
        return True


def _get_packet_scheduler():
    """Get or create the packet send scheduler thread (singleton)."""
    global _packet_scheduler
    with _scheduler_lock:
        if _packet_scheduler is None or not _packet_scheduler.is_alive():
            _packet_scheduler = PacketSendSchedulerThread()
            _packet_scheduler.start()
        return _packet_scheduler


def _get_ack_scheduler():
    """Get or create the ack send scheduler thread (singleton)."""
    global _ack_scheduler
    with _scheduler_lock:
        if _ack_scheduler is None or not _ack_scheduler.is_alive():
            _ack_scheduler = AckSendSchedulerThread()
            _ack_scheduler.start()
        return _ack_scheduler


def _send_packet_worker(msg_no: str):
    """Worker function for threadpool to send a packet.

    This function checks if the packet needs to be sent and sends it if conditions are met.
    Returns True if packet should continue to be tracked, False if done.
    """
    pkt_tracker = tracker.PacketTrack()
    packet = pkt_tracker.get(msg_no)

    if not packet:
        # Packet was acked and removed from tracker
        return False

    if packet.send_count >= packet.retry_count:
        # Reached max retry count
        LOG.info(
            f'{packet.__class__.__name__} '
            f'({packet.msgNo}) '
            'Message Send Complete. Max attempts reached'
            f' {packet.retry_count}',
        )
        pkt_tracker.remove(packet.msgNo)
        return False

    # Check if it's time to send
    send_now = False
    if packet.last_send_time:
        now = int(round(time.time()))
        sleeptime = (packet.send_count + 1) * 31
        delta = now - packet.last_send_time
        if delta > sleeptime:
            send_now = True
    else:
        send_now = True

    if send_now:
        packet.last_send_time = int(round(time.time()))
        sent = False
        try:
            sent = _send_direct(packet)
        except Exception as ex:
            LOG.error(f'Failed to send packet: {packet}')
            LOG.error(ex)
        else:
            if sent:
                packet.send_count += 1

    return True


def _send_ack_worker(msg_no: str, max_retries: int):
    """Worker function for threadpool to send an ack packet.

    This function checks if the ack needs to be sent and sends it if conditions are met.
    Returns True if ack should continue to be tracked, False if done.
    """
    pkt_tracker = tracker.PacketTrack()
    packet = pkt_tracker.get(msg_no)

    if not packet:
        # Packet was removed from tracker
        return False

    if packet.send_count >= max_retries:
        LOG.debug(
            f'{packet.__class__.__name__}'
            f'({packet.msgNo}) '
            'Send Complete. Max attempts reached'
            f' {max_retries}',
        )
        return False

    # Check if it's time to send
    send_now = False
    if packet.last_send_time:
        now = int(round(time.time()))
        sleep_time = 31
        delta = now - packet.last_send_time
        if delta > sleep_time:
            send_now = True
    else:
        # No previous send time, send immediately
        send_now = True

    if send_now:
        sent = False
        try:
            sent = _send_direct(packet)
        except Exception:
            LOG.error(f'Failed to send packet: {packet}')
        else:
            if sent:
                packet.send_count += 1
        packet.last_send_time = int(round(time.time()))

    return True


class PacketSendSchedulerThread(aprsd_threads.APRSDThread):
    """Scheduler thread that uses a threadpool to send packets.

    This thread periodically checks all packets in PacketTrack and submits
    send tasks to a threadpool executor, avoiding the need to create a
    separate thread for each packet.
    """

    def __init__(self, max_workers=5):
        super().__init__('PacketSendSchedulerThread')
        self.executor = ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix='PacketSendWorker'
        )
        self.max_workers = max_workers

    def loop(self):
        """Check all tracked packets and submit send tasks to threadpool."""
        pkt_tracker = tracker.PacketTrack()

        # Check all packets in the tracker
        for msg_no in list(pkt_tracker.keys()):
            packet = pkt_tracker.get(msg_no)
            if not packet:
                # Packet was acked, skip it
                continue

            # Skip AckPackets - they're handled by AckSendSchedulerThread
            if isinstance(packet, core.AckPacket):
                continue

            # Check if packet is still being tracked (not acked)
            if packet.send_count >= packet.retry_count:
                # Max retries reached, will be cleaned up by worker
                continue

            # Submit send task to threadpool
            # The worker will check timing and send if needed
            self.executor.submit(_send_packet_worker, msg_no)

        time.sleep(1)  # Check every second
        return True

    def _cleanup(self):
        """Cleanup threadpool executor on thread shutdown."""
        LOG.debug('Shutting down PacketSendSchedulerThread executor')
        self.executor.shutdown(wait=True)


class AckSendSchedulerThread(aprsd_threads.APRSDThread):
    """Scheduler thread that uses a threadpool to send ack packets.

    This thread periodically checks all ack packets in PacketTrack and submits
    send tasks to a threadpool executor, avoiding the need to create a
    separate thread for each ack.
    """

    def __init__(self, max_workers=3):
        super().__init__('AckSendSchedulerThread')
        self.executor = ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix='AckSendWorker'
        )
        self.max_workers = max_workers
        self.max_retries = CONF.default_ack_send_count

    def loop(self):
        """Check all tracked ack packets and submit send tasks to threadpool."""
        pkt_tracker = tracker.PacketTrack()

        # Check all packets in the tracker that are acks
        for msg_no in list(pkt_tracker.keys()):
            packet = pkt_tracker.get(msg_no)
            if not packet:
                # Packet was removed, skip it
                continue

            # Only process AckPackets
            if not isinstance(packet, core.AckPacket):
                continue

            # Check if ack is still being tracked
            if packet.send_count >= self.max_retries:
                # Max retries reached, will be cleaned up by worker
                continue

            # Submit send task to threadpool
            self.executor.submit(_send_ack_worker, msg_no, self.max_retries)

        time.sleep(1)  # Check every second
        return True

    def _cleanup(self):
        """Cleanup threadpool executor on thread shutdown."""
        LOG.debug('Shutting down AckSendSchedulerThread executor')
        self.executor.shutdown(wait=True)


class SendPacketThread(aprsd_threads.APRSDThread):
    loop_count: int = 1

    def __init__(self, packet):
        self.packet = packet
        super().__init__(f'TX-{packet.to_call}-{self.packet.msgNo}')

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
                f'{self.packet.__class__.__name__}'
                f'({self.packet.msgNo}) '
                'Message Send Complete via Ack.',
            )
            return False
        else:
            send_now = False
            if packet.send_count >= packet.retry_count:
                # we reached the send limit, don't send again
                # TODO(hemna) - Need to put this in a delayed queue?
                LOG.info(
                    f'{packet.__class__.__name__} '
                    f'({packet.msgNo}) '
                    'Message Send Complete. Max attempts reached'
                    f' {packet.retry_count}',
                )
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
                sent = False
                try:
                    sent = _send_direct(packet)
                except Exception as ex:
                    LOG.error(f'Failed to send packet: {packet}')
                    LOG.error(ex)
                else:
                    # If an exception happens while sending
                    # we don't want this attempt to count
                    # against the packet
                    if sent:
                        packet.send_count += 1

            time.sleep(1)
            # Make sure we get called again.
            self.loop_count += 1
            return True


class SendAckThread(aprsd_threads.APRSDThread):
    loop_count: int = 1
    max_retries = 3

    def __init__(self, packet):
        self.packet = packet
        super().__init__(f'TXAck-{packet.to_call}-{self.packet.msgNo}')
        self.max_retries = CONF.default_ack_send_count

    def loop(self):
        """Separate thread to send acks with retries."""
        send_now = False
        if self.packet.send_count == self.max_retries:
            # we reached the send limit, don't send again
            # TODO(hemna) - Need to put this in a delayed queue?
            LOG.debug(
                f'{self.packet.__class__.__name__}'
                f'({self.packet.msgNo}) '
                'Send Complete. Max attempts reached'
                f' {self.max_retries}',
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
                # LOG.debug(f'Still wating. {delta}')
                pass
        else:
            send_now = True

        if send_now:
            sent = False
            try:
                sent = _send_direct(self.packet)
            except Exception:
                LOG.error(f'Failed to send packet: {self.packet}')
            else:
                # If an exception happens while sending
                # we don't want this attempt to count
                # against the packet
                if sent:
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
        super().__init__('BeaconSendThread')
        self._loop_cnt = 1
        # Make sure Latitude and Longitude are set.
        if not CONF.latitude or not CONF.longitude:
            LOG.error(
                'Latitude and Longitude are not set in the config file.'
                'Beacon will not be sent and thread is STOPPED.',
            )
            self.stop()
        LOG.info(
            'Beacon thread is running and will send '
            f'beacons every {CONF.beacon_interval} seconds.',
        )

    def loop(self):
        # Only dump out the stats every N seconds
        if self._loop_cnt % CONF.beacon_interval == 0:
            pkt = core.BeaconPacket(
                from_call=CONF.callsign,
                to_call='APRS',
                latitude=float(CONF.latitude),
                longitude=float(CONF.longitude),
                comment='APRSD GPS Beacon',
                symbol=CONF.beacon_symbol,
            )
            try:
                # Only send it once
                pkt.retry_count = 1
                send(pkt, direct=True)
            except Exception as e:
                LOG.error(f'Failed to send beacon: {e}')
                APRSDClient().reset()
                time.sleep(5)

        self._loop_cnt += 1
        time.sleep(1)
        return True
