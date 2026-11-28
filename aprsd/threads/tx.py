import datetime
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from oslo_config import cfg
from rush import quota, throttle
from rush.limiters import periodic
from rush.stores import dictionary

from aprsd import conf  # noqa
from aprsd import threads as aprsd_threads
from aprsd.client.client import APRSDClient
from aprsd.packets import collector, core, tracker
from aprsd.packets import log as packet_log

CONF = cfg.CONF
LOG = logging.getLogger('APRSD')


class _LazyThrottle:
    """Throttle proxy that reads its rate limit from CONF on first use.

    The msg/ack throttles used to read CONF.msg_rate_limit_period /
    CONF.ack_rate_limit_period at module import time, which is
    import-order fragile (importing this module requires the config
    options to already be registered) and bakes the rate in at import
    time so a config change needs a restart.  This proxy defers the CONF
    read to the first check() call.
    """

    def __init__(self, conf_attr: str):
        self._conf_attr = conf_attr
        self._throttle = None

    def _get(self) -> throttle.Throttle:
        if self._throttle is None:
            self._throttle = throttle.Throttle(
                limiter=periodic.PeriodicLimiter(
                    store=dictionary.DictionaryStore(),
                ),
                rate=quota.Quota(
                    period=datetime.timedelta(
                        seconds=getattr(CONF, self._conf_attr),
                    ),
                    count=1,
                ),
            )
        return self._throttle

    def check(self, key: str, quantity: int):
        return self._get().check(key=key, quantity=quantity)


msg_t = _LazyThrottle('msg_rate_limit_period')
ack_t = _LazyThrottle('ack_rate_limit_period')
s_lock = threading.Lock()

# Global scheduler instances (singletons)
_packet_scheduler = None
_ack_scheduler = None
_scheduler_lock = threading.Lock()


def send(packet: core.Packet, direct=False, aprs_client=None):
    """Send a packet either in a thread or directly to the client."""
    # prepare the packet for sending.
    # This constructs the packet.raw
    # The lock only covers prepare/tracking: the throttle sleep in
    # _send_direct() must not run under it (see #295).
    with s_lock:
        packet.prepare(create_msg_number=True)
        # Have to call the collector to track the packet
        # After prepare, as prepare assigns the msgNo
        collector.PacketCollector().tx(packet)
    if isinstance(packet, core.AckPacket):
        if CONF.enable_sending_ack_packets:
            return _send_ack(packet, direct=direct, aprs_client=aprs_client)
        LOG.info('Sending ack packets is disabled. Not sending AckPacket.')
        return False
    return _send_packet(packet, direct=direct, aprs_client=aprs_client)


def _send_packet(packet: core.Packet, direct=False, aprs_client=None):
    if not direct:
        # The packet was already registered in PacketTrack via
        # collector.PacketCollector().tx(packet) in send() before this
        # function was called.  PacketSendSchedulerThread polls PacketTrack
        # every second and will find the packet there — nothing more needs
        # to be done here.  The scheduler is started (or confirmed alive)
        # as a side-effect of _get_packet_scheduler().
        scheduler = _get_packet_scheduler()
        if not (scheduler and scheduler.is_alive()):
            # Fallback: scheduler failed to start — send directly in a thread
            thread = SendPacketThread(packet=packet)
            thread.start()
        # Queued. The scheduler sends it later, so this is not a wire ack.
        return True
    return _send_direct(packet, aprs_client=aprs_client)


def _send_ack(packet: core.AckPacket, direct=False, aprs_client=None):
    if not direct:
        # Same implicit handoff as _send_packet: the ack was registered in
        # PacketTrack before this call; AckSendSchedulerThread polls and
        # picks it up.  Starting/verifying the scheduler is all that's needed.
        scheduler = _get_ack_scheduler()
        if not (scheduler and scheduler.is_alive()):
            # Fallback: scheduler failed to start — send directly in a thread
            thread = SendAckThread(packet=packet)
            thread.start()
        return True
    return _send_direct(packet, aprs_client=aprs_client)


def _send_direct(packet, aprs_client=None):
    # Acks are limited by ack_rate_limit_period, non-acks by
    # msg_rate_limit_period.  Every transmission (first attempt and retries)
    # passes through here, so each one is charged against its quota once.
    t = ack_t if isinstance(packet, core.AckPacket) else msg_t
    while True:
        result = t.check(key='tx', quantity=1)
        if not result.limited:
            break
        time.sleep(result.retry_after.total_seconds())
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


def _packet_send_due(packet):
    """True when the next message retry is due.

    Message retries back off as the attempt count grows: 31s, 62s, 93s...
    """
    if not packet.last_send_time:
        return True
    now = int(round(time.time()))
    return now - packet.last_send_time > (packet.send_count + 1) * 31


def _ack_send_due(packet):
    """True when the next ack retry is due.

    Acks retry on a fixed 31s cadence.  APRS duplicate suppression is
    ~30s, so a shorter gap is dropped by the receiving station.
    """
    if not packet.last_send_time:
        return True
    now = int(round(time.time()))
    return now - packet.last_send_time > 31


def _packet_attempt(packet):
    """Run one send/retry step for a non-ack packet.

    Returns False when the packet is out of retries; that path removes it
    from PacketTrack.  An acked packet never reaches here: the caller sees
    it missing from the tracker and returns False before calling this.
    """
    if packet.send_count >= packet.retry_count:
        LOG.info(
            f'{packet.__class__.__name__} '
            f'({packet.msgNo}) '
            'Message Send Complete. Max attempts reached'
            f' {packet.retry_count}',
        )
        tracker.PacketTrack().remove(packet.msgNo)
        return False

    if not _packet_send_due(packet):
        return True

    # Stamp before sending so a slow or throttled send is not retried
    # immediately; send_count only moves on a successful send.
    packet.last_send_time = int(round(time.time()))
    try:
        sent = _send_direct(packet)
    except Exception as ex:
        LOG.error(f'Failed to send packet: {packet}')
        LOG.error(ex)
    else:
        if sent:
            packet.send_count += 1
    return True


def _ack_attempt(packet, max_retries):
    """Run one send/retry step for an ack packet.

    Returns False when the ack is out of retries; that path removes it from
    PacketTrack.  Acks stamp last_send_time after the attempt instead of
    before, because their cadence is fixed.
    """
    if packet.send_count >= max_retries:
        LOG.debug(
            f'{packet.__class__.__name__}'
            f'({packet.msgNo}) '
            'Send Complete. Max attempts reached'
            f' {max_retries}',
        )
        tracker.PacketTrack().remove(packet.msgNo)
        return False

    if not _ack_send_due(packet):
        return True

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


def _send_packet_worker(msg_no: str):
    """Threadpool entry point: one retry step for the tracked message."""
    packet = tracker.PacketTrack().get(msg_no)

    if not packet:
        # Packet was acked and removed from tracker
        return False

    return _packet_attempt(packet)


def _send_ack_worker(msg_no: str, max_retries: int):
    """Threadpool entry point: one retry step for the tracked ack."""
    packet = tracker.PacketTrack().get(msg_no)

    if not packet:
        # Packet was removed from tracker
        return False

    return _ack_attempt(packet, max_retries)


class PacketSendSchedulerThread(aprsd_threads.APRSDThread):
    """Scheduler thread that uses a threadpool to send packets.

    This thread periodically checks all packets in PacketTrack and submits
    send tasks to a threadpool executor, avoiding the need to create a
    separate thread for each packet.
    """

    daemon = False  # Non-daemon for graceful packet handling

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
                # Max retries reached, clean up
                pkt_tracker.remove(msg_no)
                continue

            # Don't submit if we sent recently (prevents threadpool race
            # where multiple workers fire before send_count is incremented)
            if not _packet_send_due(packet):
                continue

            # Submit send task to threadpool
            # The worker will check timing and send if needed
            self.executor.submit(_send_packet_worker, msg_no)

        self.wait()  # Check every period (default 1 second)
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

    daemon = False  # Non-daemon for graceful ACK handling

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
                # Max retries reached, clean up
                pkt_tracker.remove(msg_no)
                continue

            # Don't submit if we sent recently (prevents threadpool race
            # where multiple workers fire before send_count is incremented)
            if not _ack_send_due(packet):
                continue

            # Submit send task to threadpool
            self.executor.submit(_send_ack_worker, msg_no, self.max_retries)

        self.wait()  # Check every period (default 1 second)
        return True

    def _cleanup(self):
        """Cleanup threadpool executor on thread shutdown."""
        LOG.debug('Shutting down AckSendSchedulerThread executor')
        self.executor.shutdown(wait=True)


class SendPacketThread(aprsd_threads.APRSDThread):
    """Fallback thread for when the packet scheduler fails to start."""

    def __init__(self, packet):
        self.packet = packet
        super().__init__(f'TX-{packet.to_call}-{self.packet.msgNo}')

    def loop(self):
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

        if not _packet_attempt(packet):
            return False

        self.wait()
        # Make sure we get called again.
        return True


class SendAckThread(aprsd_threads.APRSDThread):
    """Fallback thread for when the ack scheduler fails to start."""

    max_retries = 3

    def __init__(self, packet):
        self.packet = packet
        super().__init__(f'TXAck-{packet.to_call}-{self.packet.msgNo}')
        self.max_retries = CONF.default_ack_send_count

    def loop(self):
        """Separate thread to send acks with retries."""
        if not _ack_attempt(self.packet, self.max_retries):
            return False

        self.wait()
        return True


class BeaconSendThread(aprsd_threads.APRSDThread):
    """Thread that sends a GPS beacon packet periodically.

    Settings are in the [DEFAULT] section of the config file.
    """

    def __init__(self):
        super().__init__('BeaconSendThread')
        self.period = CONF.beacon_interval
        # Make sure Latitude and Longitude are set.
        if not CONF.latitude or not CONF.longitude:
            LOG.error(
                'Latitude and Longitude are not set in the config file.'
                'Beacon will not be sent and thread is STOPPED.',
            )
            self.stop()
        else:
            # CONF.latitude/longitude are StrOpt, so validate they parse
            # as floats up front.  Otherwise loop()'s float() would raise
            # a ValueError outside its try/except and kill the thread.
            try:
                self.latitude = float(CONF.latitude)
                self.longitude = float(CONF.longitude)
            except (TypeError, ValueError):
                LOG.error(
                    'Latitude and Longitude must be numeric in the config file.'
                    'Beacon will not be sent and thread is STOPPED.',
                )
                self.stop()
        LOG.info(
            'Beacon thread is running and will send '
            f'beacons every {CONF.beacon_interval} seconds.',
        )

    def loop(self):
        pkt = core.BeaconPacket(
            from_call=CONF.callsign,
            to_call='APRS',
            position=core.Position(
                latitude=self.latitude,
                longitude=self.longitude,
                comment='APRSD GPS Beacon',
                symbol=CONF.beacon_symbol,
            ),
        )
        try:
            # Only send it once
            pkt.retry_count = 1
            send(pkt, direct=True)
        except Exception as e:
            LOG.error(f'Failed to send beacon: {e}')
            APRSDClient().reset()
            if self.wait(timeout=5):
                return False

        self.wait()
        return True
