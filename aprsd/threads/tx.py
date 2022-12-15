import datetime
import logging
import time

from aprsd import client, stats
from aprsd import threads as aprsd_threads
from aprsd.packets import packet_list, tracker


LOG = logging.getLogger("APRSD")


class SendPacketThread(aprsd_threads.APRSDThread):
    def __init__(self, packet):
        self.packet = packet
        name = self.packet.raw[:5]
        super().__init__(f"TXPKT-{self.packet.msgNo}-{name}")
        pkt_tracker = tracker.PacketTrack()
        pkt_tracker.add(packet)

    def loop(self):
        LOG.debug("TX Loop")
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
            LOG.info("Message Send Complete via Ack.")
            return False
        else:
            send_now = False
            if packet._last_send_attempt == packet._retry_count:
                # we reached the send limit, don't send again
                # TODO(hemna) - Need to put this in a delayed queue?
                LOG.info("Message Send Complete. Max attempts reached.")
                if not packet._allow_delay:
                    pkt_tracker.remove(packet.msgNo)
                return False

            # Message is still outstanding and needs to be acked.
            if packet._last_send_time:
                # Message has a last send time tracking
                now = datetime.datetime.now()
                sleeptime = (packet._last_send_attempt + 1) * 31
                delta = now - packet._last_send_time
                if delta > datetime.timedelta(seconds=sleeptime):
                    # It's time to try to send it again
                    send_now = True
            else:
                send_now = True

            if send_now:
                # no attempt time, so lets send it, and start
                # tracking the time.
                packet.log("Sending Message")
                cl = client.factory.create().client
                cl.send(packet.raw)
                stats.APRSDStats().msgs_tx_inc()
                packet_list.PacketList().add(packet)
                packet._last_send_time = datetime.datetime.now()
                packet._last_send_attempt += 1

            time.sleep(5)
            # Make sure we get called again.
            return True


class SendAckThread(aprsd_threads.APRSDThread):
    def __init__(self, packet):
        self.packet = packet
        super().__init__(f"SendAck-{self.packet.msgNo}")
        self._loop_cnt = 1

    def loop(self):
        """Separate thread to send acks with retries."""
        send_now = False
        if self.packet._last_send_attempt == self.packet._retry_count:
            # we reached the send limit, don't send again
            # TODO(hemna) - Need to put this in a delayed queue?
            LOG.info("Ack Send Complete. Max attempts reached.")
            return False

        if self.packet._last_send_time:
            # Message has a last send time tracking
            now = datetime.datetime.now()

            # aprs duplicate detection is 30 secs?
            # (21 only sends first, 28 skips middle)
            sleeptime = 31
            delta = now - self.packet._last_send_time
            if delta > datetime.timedelta(seconds=sleeptime):
                # It's time to try to send it again
                send_now = True
            elif self._loop_cnt % 5 == 0:
                LOG.debug(f"Still wating. {delta}")
        else:
            send_now = True

        if send_now:
            cl = client.factory.create().client
            self.packet.log("Sending ACK")
            cl.send(self.packet.raw)
            self.packet._send_count += 1
            stats.APRSDStats().ack_tx_inc()
            packet_list.PacketList().add(self.packet)
            self.packet._last_send_attempt += 1
            self.packet._last_send_time = datetime.datetime.now()
        time.sleep(1)
        self._loop_cnt += 1
        return True
