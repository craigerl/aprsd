# Daemon Threads and Event-Based Timing Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor all APRSD thread classes to use daemon threads and `threading.Event()` for interruptible waits and cleaner periodic timing.

**Architecture:** Modify `APRSDThread` base class to add `daemon` and `period` class attributes, replace boolean `thread_stop` with `threading.Event`, add `wait()` method. Update all 15 subclasses to use new pattern.

**Tech Stack:** Python threading, threading.Event, existing APRSD thread infrastructure

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `aprsd/threads/aprsd.py` | Modify | Base class + ThreadList changes |
| `aprsd/threads/keepalive.py` | Modify | KeepAliveThread period migration |
| `aprsd/threads/stats.py` | Modify | 3 stats threads, APRSDStatsStoreThread non-daemon |
| `aprsd/threads/rx.py` | Modify | 4 RX threads with queue-based waits |
| `aprsd/threads/tx.py` | Modify | 5 TX threads, 2 schedulers non-daemon |
| `aprsd/threads/registry.py` | Modify | APRSRegistryThread period from config |
| `aprsd/cmds/listen.py` | Modify | APRSDListenProcessThread (inherits from APRSDFilterThread) |
| `aprsd/main.py` | Modify | Signal handler update |
| `tests/threads/test_aprsd_thread.py` | Modify | Update existing tests for Event-based API |

---

## Chunk 1: Base Class Refactor

### Task 1: Update APRSDThread base class

**Files:**
- Modify: `aprsd/threads/aprsd.py:13-76`
- Test: `tests/threads/test_aprsd_thread.py`

- [ ] **Step 1: Write failing test for daemon attribute**

**Note:** The existing test file already has a `TestThread` fixture class with a `should_loop` parameter. Tests in this plan use that existing fixture.

Add to `tests/threads/test_aprsd_thread.py`:

```python
def test_daemon_attribute_default(self):
    """Test that daemon attribute defaults to True."""
    thread = TestThread('DaemonTest')
    self.assertTrue(thread.daemon)


def test_daemon_attribute_override(self):
    """Test that daemon attribute can be overridden via class attribute."""
    class NonDaemonThread(APRSDThread):
        daemon = False
        def loop(self):
            return False

    thread = NonDaemonThread('NonDaemonTest')
    self.assertFalse(thread.daemon)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/threads/test_aprsd_thread.py::TestAPRSDThread::test_daemon_attribute_default -v`
Expected: FAIL with `AssertionError` (daemon is False by default currently)

- [ ] **Step 3: Write failing test for period attribute**

Add to `tests/threads/test_aprsd_thread.py`:

```python
def test_period_attribute_default(self):
    """Test that period attribute defaults to 1."""
    thread = TestThread('PeriodTest')
    self.assertEqual(thread.period, 1)


def test_period_attribute_override(self):
    """Test that period attribute can be overridden via class attribute."""
    class LongPeriodThread(APRSDThread):
        period = 60
        def loop(self):
            return False

    thread = LongPeriodThread('LongPeriodTest')
    self.assertEqual(thread.period, 60)
```

- [ ] **Step 4: Run test to verify it fails**

Run: `pytest tests/threads/test_aprsd_thread.py::TestAPRSDThread::test_period_attribute_default -v`
Expected: FAIL with `AttributeError: 'TestThread' object has no attribute 'period'`

- [ ] **Step 5: Write failing test for _shutdown_event and wait()**

Add to `tests/threads/test_aprsd_thread.py`:

```python
def test_shutdown_event_exists(self):
    """Test that _shutdown_event is created."""
    thread = TestThread('EventTest')
    self.assertIsInstance(thread._shutdown_event, threading.Event)
    self.assertFalse(thread._shutdown_event.is_set())


def test_wait_returns_false_on_timeout(self):
    """Test that wait() returns False when timeout expires."""
    thread = TestThread('WaitTimeoutTest')
    start = time.time()
    result = thread.wait(timeout=0.1)
    elapsed = time.time() - start
    self.assertFalse(result)
    self.assertGreaterEqual(elapsed, 0.1)


def test_wait_returns_true_when_stopped(self):
    """Test that wait() returns True immediately when stop() was called."""
    thread = TestThread('WaitStopTest')
    thread.stop()
    start = time.time()
    result = thread.wait(timeout=10)  # Would timeout in 10s if not stopped
    elapsed = time.time() - start
    self.assertTrue(result)
    self.assertLess(elapsed, 1)  # Should return immediately


def test_wait_uses_period_by_default(self):
    """Test that wait() uses self.period when no timeout specified."""
    class ShortPeriodThread(APRSDThread):
        period = 0.1
        def loop(self):
            return False

    thread = ShortPeriodThread('ShortPeriodTest')
    start = time.time()
    result = thread.wait()
    elapsed = time.time() - start
    self.assertFalse(result)
    self.assertGreaterEqual(elapsed, 0.1)
    self.assertLess(elapsed, 0.5)
```

- [ ] **Step 6: Run tests to verify they fail**

Run: `pytest tests/threads/test_aprsd_thread.py -k "shutdown_event or wait_" -v`
Expected: FAIL with `AttributeError`

- [ ] **Step 7: Implement base class changes**

Update `aprsd/threads/aprsd.py`:

```python
import abc
import datetime
import logging
import threading
import time
from typing import List

import wrapt

LOG = logging.getLogger('APRSD')


class APRSDThread(threading.Thread, metaclass=abc.ABCMeta):
    """Base class for all threads in APRSD."""

    # Class attributes - subclasses override as needed
    daemon = True  # Most threads are daemon threads
    period = 1     # Default wait period in seconds
    loop_count = 1
    _pause = False

    def __init__(self, name):
        super().__init__(name=name)
        # Set daemon from class attribute
        self.daemon = self.__class__.daemon
        # Set period from class attribute (can be overridden in __init__)
        self.period = self.__class__.period
        self._shutdown_event = threading.Event()
        self.loop_count = 0
        APRSDThreadList().add(self)
        self._last_loop = datetime.datetime.now()

    def _should_quit(self):
        """Check if thread should exit."""
        return self._shutdown_event.is_set()

    def pause(self):
        """Logically pause the processing of the main loop."""
        LOG.debug(f"Pausing thread '{self.name}' loop_count {self.loop_count}")
        self._pause = True

    def unpause(self):
        """Logically resume processing of the main loop."""
        LOG.debug(f"Resuming thread '{self.name}' loop_count {self.loop_count}")
        self._pause = False

    def stop(self):
        """Signal thread to stop. Returns immediately."""
        LOG.debug(f"Stopping thread '{self.name}'")
        self._shutdown_event.set()

    def wait(self, timeout: float | None = None) -> bool:
        """Wait for shutdown signal or timeout.

        Args:
            timeout: Seconds to wait. Defaults to self.period.

        Returns:
            True if shutdown was signaled, False if timeout expired.
        """
        wait_time = timeout if timeout is not None else self.period
        return self._shutdown_event.wait(timeout=wait_time)

    @abc.abstractmethod
    def loop(self):
        pass

    def _cleanup(self):
        """Add code to subclass to do any cleanup"""

    def __str__(self):
        out = (
            f'Thread <{self.__class__.__name__}({self.name}) Alive? {self.is_alive()}>'
        )
        return out

    def loop_age(self):
        """How old is the last loop call?"""
        return datetime.datetime.now() - self._last_loop

    def run(self):
        LOG.debug('Starting')
        while not self._should_quit():
            if self._pause:
                self.wait(timeout=1)
            else:
                self.loop_count += 1
                can_loop = self.loop()
                self._last_loop = datetime.datetime.now()
                if not can_loop:
                    self.stop()
        self._cleanup()
        APRSDThreadList().remove(self)
        LOG.debug('Exiting')
```

- [ ] **Step 8: Run base class tests to verify they pass**

Run: `pytest tests/threads/test_aprsd_thread.py::TestAPRSDThread -v`
Expected: PASS

- [ ] **Step 9: Update existing tests that reference thread_stop**

Update `tests/threads/test_aprsd_thread.py` - change references from `thread_stop` to `_shutdown_event.is_set()`:

```python
def test_init(self):
    """Test thread initialization."""
    thread = TestThread('TestThread1')
    self.assertEqual(thread.name, 'TestThread1')
    self.assertFalse(thread._shutdown_event.is_set())
    self.assertFalse(thread._pause)
    # Note: loop_count starts at 0 now (was 1)
    self.assertEqual(thread.loop_count, 0)

    # Should be registered in thread list
    thread_list = APRSDThreadList()
    self.assertIn(thread, thread_list.threads_list)


def test_should_quit(self):
    """Test _should_quit() method."""
    thread = TestThread('TestThread2')
    self.assertFalse(thread._should_quit())

    thread._shutdown_event.set()
    self.assertTrue(thread._should_quit())


def test_stop(self):
    """Test stop() method."""
    thread = TestThread('TestThread4')
    self.assertFalse(thread._shutdown_event.is_set())

    thread.stop()
    self.assertTrue(thread._shutdown_event.is_set())


def test_stop_all(self):
    """Test stop_all() method."""
    thread_list = APRSDThreadList()
    thread1 = TestThread('TestThread8')
    thread2 = TestThread('TestThread9')
    thread_list.add(thread1)
    thread_list.add(thread2)

    thread_list.stop_all()
    self.assertTrue(thread1._shutdown_event.is_set())
    self.assertTrue(thread2._shutdown_event.is_set())
```

- [ ] **Step 10: Run all base class tests**

Run: `pytest tests/threads/test_aprsd_thread.py -v`
Expected: PASS

- [ ] **Step 11: Commit base class changes**

```bash
git add aprsd/threads/aprsd.py tests/threads/test_aprsd_thread.py
git commit -m "refactor(threads): add daemon, period, Event-based shutdown to APRSDThread

- Add daemon=True class attribute (subclasses override to False)
- Add period=1 class attribute for wait interval
- Replace thread_stop boolean with _shutdown_event (threading.Event)
- Add wait() method for interruptible sleeps
- Update tests for new Event-based API

BREAKING: thread_stop boolean replaced with _shutdown_event.
Code checking thread.thread_stop directly must use thread._shutdown_event.is_set()"
```

---

### Task 2: Add join_non_daemon to APRSDThreadList

**Files:**
- Modify: `aprsd/threads/aprsd.py:79-169`
- Test: `tests/threads/test_aprsd_thread.py`

- [ ] **Step 1: Write failing test for join_non_daemon**

Add to `tests/threads/test_aprsd_thread.py`:

```python
def test_join_non_daemon(self):
    """Test join_non_daemon() waits for non-daemon threads."""
    class NonDaemonTestThread(APRSDThread):
        daemon = False
        def __init__(self, name):
            super().__init__(name)
            self.finished = False

        def loop(self):
            time.sleep(0.2)
            self.finished = True
            return False

    thread_list = APRSDThreadList()
    thread = NonDaemonTestThread('NonDaemonJoinTest')
    thread_list.add(thread)
    thread.start()

    # Stop triggers the event, thread should finish its loop then exit
    thread.stop()
    thread_list.join_non_daemon(timeout=5.0)

    self.assertTrue(thread.finished or not thread.is_alive())


def test_join_non_daemon_skips_daemon_threads(self):
    """Test join_non_daemon() does not wait for daemon threads."""
    thread_list = APRSDThreadList()
    # Clear existing threads
    thread_list.threads_list = []

    # Create a daemon thread that loops forever
    thread = TestThread('DaemonSkipTest', should_loop=True)
    thread_list.add(thread)
    thread.start()

    # This should return quickly since it's a daemon thread
    start = time.time()
    thread_list.join_non_daemon(timeout=0.1)
    elapsed = time.time() - start

    self.assertLess(elapsed, 0.5)  # Should not wait for daemon

    # Cleanup
    thread.stop()
    thread.join(timeout=1)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/threads/test_aprsd_thread.py::TestAPRSDThreadList::test_join_non_daemon -v`
Expected: FAIL with `AttributeError: 'APRSDThreadList' object has no attribute 'join_non_daemon'`

- [ ] **Step 3: Implement join_non_daemon method**

Add to `APRSDThreadList` class in `aprsd/threads/aprsd.py`:

```python
@wrapt.synchronized(lock)
def join_non_daemon(self, timeout: float = 5.0):
    """Wait for non-daemon threads to complete gracefully.

    Args:
        timeout: Maximum seconds to wait per thread.
    """
    for th in self.threads_list:
        if not th.daemon and th.is_alive():
            LOG.info(f'Waiting for non-daemon thread {th.name} to finish')
            th.join(timeout=timeout)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/threads/test_aprsd_thread.py::TestAPRSDThreadList::test_join_non_daemon -v`
Expected: PASS

- [ ] **Step 5: Commit ThreadList changes**

```bash
git add aprsd/threads/aprsd.py tests/threads/test_aprsd_thread.py
git commit -m "feat(threads): add join_non_daemon() to APRSDThreadList

Allows graceful shutdown by waiting for non-daemon threads to complete
while allowing daemon threads to be terminated immediately."
```

---

## Chunk 2: Stats and Keepalive Thread Migration

### Task 3: Migrate KeepAliveThread

**Files:**
- Modify: `aprsd/threads/keepalive.py`

- [ ] **Step 1: Update KeepAliveThread to use period**

Replace the loop method in `aprsd/threads/keepalive.py`:

```python
class KeepAliveThread(APRSDThread):
    cntr = 0
    checker_time = datetime.datetime.now()
    period = 60  # Run keepalive every 60 seconds

    def __init__(self):
        tracemalloc.start()
        super().__init__('KeepAlive')
        max_timeout = {'hours': 0.0, 'minutes': 2, 'seconds': 0}
        self.max_delta = datetime.timedelta(**max_timeout)

    def loop(self):
        stats_json = collector.Collector().collect()
        pl = packets.PacketList()
        thread_list = APRSDThreadList()
        now = datetime.datetime.now()

        if (
            'APRSClientStats' in stats_json
            and stats_json['APRSClientStats'].get('transport') == 'aprsis'
        ):
            if stats_json['APRSClientStats'].get('server_keepalive'):
                last_msg_time = utils.strfdelta(
                    now - stats_json['APRSClientStats']['server_keepalive']
                )
            else:
                last_msg_time = 'N/A'
        else:
            last_msg_time = 'N/A'

        tracked_packets = stats_json['PacketTrack']['total_tracked']
        tx_msg = 0
        rx_msg = 0
        if 'PacketList' in stats_json:
            msg_packets = stats_json['PacketList'].get('MessagePacket')
            if msg_packets:
                tx_msg = msg_packets.get('tx', 0)
                rx_msg = msg_packets.get('rx', 0)

        keepalive = (
            '{} - Uptime {} RX:{} TX:{} Tracker:{} Msgs TX:{} RX:{} '
            'Last:{} - RAM Current:{} Peak:{} Threads:{} LoggingQueue:{}'
        ).format(
            stats_json['APRSDStats']['callsign'],
            stats_json['APRSDStats']['uptime'],
            pl.total_rx(),
            pl.total_tx(),
            tracked_packets,
            tx_msg,
            rx_msg,
            last_msg_time,
            stats_json['APRSDStats']['memory_current_str'],
            stats_json['APRSDStats']['memory_peak_str'],
            len(thread_list),
            aprsd_log.logging_queue.qsize(),
        )
        LOG.info(keepalive)
        if 'APRSDThreadList' in stats_json:
            thread_list = stats_json['APRSDThreadList']
            for thread_name in thread_list:
                thread = thread_list[thread_name]
                alive = thread['alive']
                age = thread['age']
                key = thread['name']
                if not alive:
                    LOG.error(f'Thread {thread}')

                thread_hex = f'fg {utils.hex_from_name(key)}'
                t_name = f'<{thread_hex}>{key:<15}</{thread_hex}>'
                thread_msg = f'{t_name} Alive? {str(alive): <5} {str(age): <20}'
                LOGU.opt(colors=True).info(thread_msg)

        # Go through the registered keepalive collectors
        # and check them as well as call log.
        collect = keepalive_collector.KeepAliveCollector()
        collect.check()
        collect.log()

        # Check version every day
        delta = now - self.checker_time
        if delta > datetime.timedelta(hours=24):
            self.checker_time = now
            level, msg = utils._check_version()
            if level:
                LOG.warning(msg)
        self.cntr += 1

        self.wait()  # Wait for period (60s) or shutdown signal
        return True
```

- [ ] **Step 2: Run existing tests**

Run: `pytest tests/ -k keepalive -v`
Expected: PASS (or skip if no specific keepalive tests)

- [ ] **Step 3: Commit KeepAliveThread changes**

```bash
git add aprsd/threads/keepalive.py
git commit -m "refactor(threads): migrate KeepAliveThread to Event-based timing

- Set period=60 class attribute
- Remove counter-based conditional (loop_count % 60)
- Replace time.sleep(1) with self.wait()"
```

---

### Task 4: Migrate Stats Threads

**Files:**
- Modify: `aprsd/threads/stats.py`

- [ ] **Step 1: Update APRSDStatsStoreThread (non-daemon)**

```python
class APRSDStatsStoreThread(APRSDThread):
    """Save APRSD Stats to disk periodically."""

    daemon = False  # Non-daemon for graceful disk writes
    period = 10     # Save every 10 seconds

    def __init__(self):
        super().__init__('StatsStore')

    def loop(self):
        stats = collector.Collector().collect()
        ss = StatsStore()
        ss.add(stats)
        ss.save()

        self.wait()  # Wait for period (10s) or shutdown signal
        return True
```

- [ ] **Step 2: Update APRSDPushStatsThread**

```python
class APRSDPushStatsThread(APRSDThread):
    """Push the local stats to a remote API."""

    def __init__(
        self, push_url=None, frequency_seconds=None, send_packetlist: bool = False
    ):
        super().__init__('PushStats')
        self.push_url = push_url if push_url else CONF.push_stats.push_url
        # Set period from config
        self.period = (
            frequency_seconds
            if frequency_seconds
            else CONF.push_stats.frequency_seconds
        )
        self.send_packetlist = send_packetlist

    def loop(self):
        stats_json = collector.Collector().collect(serializable=True)
        url = f'{self.push_url}/stats'
        headers = {'Content-Type': 'application/json'}
        # Remove the PacketList section to reduce payload size
        if not self.send_packetlist:
            if 'PacketList' in stats_json:
                del stats_json['PacketList']['packets']

        now = datetime.datetime.now()
        time_format = '%m-%d-%Y %H:%M:%S'
        stats = {
            'time': now.strftime(time_format),
            'stats': stats_json,
        }

        try:
            response = requests.post(url, json=stats, headers=headers, timeout=5)
            response.raise_for_status()

            if response.status_code == 200:
                LOGU.info(f'Successfully pushed stats to {self.push_url}')
            else:
                LOGU.warning(
                    f'Failed to push stats to {self.push_url}: HTTP {response.status_code}'
                )

        except requests.exceptions.RequestException as e:
            LOGU.error(f'Error pushing stats to {self.push_url}: {e}')
        except Exception as e:
            LOGU.error(f'Unexpected error in stats push: {e}')

        self.wait()  # Wait for period or shutdown signal
        return True
```

- [ ] **Step 3: Update StatsLogThread**

```python
class StatsLogThread(APRSDThread):
    """Log the stats from the PacketList."""

    period = 10  # Log every 10 seconds

    def __init__(self):
        super().__init__('PacketStatsLog')
        self._last_total_rx = 0
        self.start_time = time.time()

    def loop(self):
        # log the stats every period seconds
        stats_json = collector.Collector().collect(serializable=True)
        stats = stats_json['PacketList']
        total_rx = stats['rx']
        rx_delta = total_rx - self._last_total_rx
        rate = rx_delta / self.period

        # Get unique callsigns count from SeenList stats
        seen_list_instance = seen_list.SeenList()
        seen_list_stats = seen_list_instance.stats()
        seen_list_instance.save()
        seen_list_stats = seen_list_stats.copy()
        unique_callsigns_count = len(seen_list_stats)

        # Calculate uptime
        elapsed = time.time() - self.start_time
        elapsed_minutes = elapsed / 60
        elapsed_hours = elapsed / 3600

        # Log summary stats
        LOGU.opt(colors=True).info(
            f'<green>RX Rate: {rate:.2f} pps</green>  '
            f'<yellow>Total RX: {total_rx}</yellow> '
            f'<red>RX Last {self.period} secs: {rx_delta}</red> '
        )
        LOGU.opt(colors=True).info(
            f'<cyan>Uptime: {elapsed:.0f}s ({elapsed_minutes:.1f}m / {elapsed_hours:.2f}h)</cyan>  '
            f'<magenta>Unique Callsigns: {unique_callsigns_count}</magenta>',
        )
        self._last_total_rx = total_rx

        # Log individual type stats, sorted by RX count (descending)
        sorted_types = sorted(
            stats['types'].items(), key=lambda x: x[1]['rx'], reverse=True
        )
        for k, v in sorted_types:
            percentage = (v['rx'] / total_rx * 100) if total_rx > 0 else 0.0
            packet_type_str = f'{k:<15}'
            rx_count_str = f'{v["rx"]:6d}'
            tx_count_str = f'{v["tx"]:6d}'
            percentage_str = f'{percentage:5.1f}%'
            rx_color_tag = (
                'green' if v['rx'] > 100 else 'yellow' if v['rx'] > 10 else 'red'
            )
            LOGU.opt(colors=True).info(
                f'  <cyan>{packet_type_str}</cyan>: '
                f'<{rx_color_tag}>RX: {rx_count_str}</{rx_color_tag}> '
                f'<red>TX: {tx_count_str}</red> '
                f'<magenta>({percentage_str})</magenta>',
            )

        # Extract callsign counts from seen_list stats
        callsign_counts = {}
        for callsign, data in seen_list_stats.items():
            if isinstance(data, dict) and 'count' in data:
                callsign_counts[callsign] = data['count']

        # Sort callsigns by packet count (descending) and get top 10
        sorted_callsigns = sorted(
            callsign_counts.items(), key=lambda x: x[1], reverse=True
        )[:10]

        # Log top 10 callsigns
        if sorted_callsigns:
            LOGU.opt(colors=True).info(
                '<cyan>Top 10 Callsigns by Packet Count:</cyan>'
            )
            total_ranks = len(sorted_callsigns)
            for rank, (callsign, count) in enumerate(sorted_callsigns, 1):
                percentage = (count / total_rx * 100) if total_rx > 0 else 0.0
                if rank == 1:
                    count_color_tag = 'red'
                elif rank == total_ranks:
                    count_color_tag = 'green'
                else:
                    count_color_tag = 'yellow'
                LOGU.opt(colors=True).info(
                    f'  <cyan>{rank:2d}.</cyan> '
                    f'<white>{callsign:<12}</white>: '
                    f'<{count_color_tag}>{count:6d} packets</{count_color_tag}> '
                    f'<magenta>({percentage:5.1f}%)</magenta>',
                )

        self.wait()  # Wait for period (10s) or shutdown signal
        return True
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/ -v`
Expected: PASS

- [ ] **Step 5: Commit stats thread changes**

```bash
git add aprsd/threads/stats.py
git commit -m "refactor(threads): migrate stats threads to Event-based timing

- APRSDStatsStoreThread: daemon=False, period=10
- APRSDPushStatsThread: period from config
- StatsLogThread: period=10
- Remove counter-based conditionals
- Replace time.sleep(1) with self.wait()"
```

---

## Chunk 3: RX Thread Migration

### Task 5: Migrate RX Threads

**Files:**
- Modify: `aprsd/threads/rx.py`

- [ ] **Step 1: Update APRSDRXThread**

```python
class APRSDRXThread(APRSDThread):
    """Thread to receive packets from the APRS Client."""

    _client = None
    packet_queue = None
    pkt_count = 0

    def __init__(self, packet_queue: queue.Queue):
        super().__init__('RX_PKT')
        self.packet_queue = packet_queue

    def stop(self):
        self._shutdown_event.set()
        if self._client:
            self._client.close()

    def loop(self):
        if not self._client:
            self._client = APRSDClient()
            self.wait(timeout=1)
            return True

        if not self._client.is_alive:
            self._client = APRSDClient()
            self.wait(timeout=1)
            return True

        try:
            self._client.consumer(
                self.process_packet,
                raw=True,
            )
        except (
            aprslib.exceptions.ConnectionDrop,
            aprslib.exceptions.ConnectionError,
        ):
            LOG.error('Connection dropped, reconnecting')
            self._client.reset()
            if self.wait(timeout=5):  # Interruptible 5s wait
                return False  # Shutdown signaled
        except Exception as ex:
            LOG.exception(ex)
            LOG.error('Resetting connection and trying again.')
            self._client.reset()
            if self.wait(timeout=5):  # Interruptible 5s wait
                return False  # Shutdown signaled
        return True

    def process_packet(self, *args, **kwargs):
        """Put the raw packet on the queue."""
        if args:
            data = args[0]
        elif 'raw' in kwargs:
            data = kwargs['raw']
        elif 'frame' in kwargs:
            data = kwargs['frame']
        elif 'packet' in kwargs:
            data = kwargs['packet']
        else:
            LOG.warning('No frame received to process?!?!')
            return

        self.pkt_count += 1
        self.packet_queue.put(data)
```

- [ ] **Step 2: Update APRSDFilterThread (queue-based wait)**

```python
class APRSDFilterThread(APRSDThread):
    """Thread to filter packets on the packet queue."""

    def __init__(self, thread_name: str, packet_queue: queue.Queue):
        super().__init__(thread_name)
        self.packet_queue = packet_queue
        self.packet_count = 0
        self._client = APRSDClient()

    def filter_packet(self, packet: type[core.Packet]) -> type[core.Packet] | None:
        if not filter.PacketFilter().filter(packet):
            return None
        return packet

    def print_packet(self, packet):
        packet_log.log(packet, packet_count=self.packet_count)

    def loop(self):
        try:
            # Queue timeout serves as interruptible wait
            pkt = self.packet_queue.get(timeout=self.period)
            self.packet_count += 1
            packet = self._client.decode_packet(pkt)
            if not packet:
                LOG.debug(f'Packet failed to parse. "{pkt}"')
                return True
            self.print_packet(packet)
            if packet:
                if self.filter_packet(packet):
                    collector.PacketCollector().rx(packet)
                    self.process_packet(packet)
        except queue.Empty:
            pass  # Normal timeout, loop will check _should_quit
        return True
```

Note: `APRSDProcessPacketThread` and `APRSDPluginProcessPacketThread` extend `APRSDFilterThread` and inherit the queue-based wait pattern. They don't need changes to their `loop()` method as they override `process_packet()` and `process_our_message_packet()`.

- [ ] **Step 3: Verify APRSDListenProcessThread (listen.py) inherits changes**

`APRSDListenProcessThread` in `aprsd/cmds/listen.py` extends `APRSDFilterThread`. It inherits the queue-based wait pattern automatically. No code changes needed in `listen.py` - verify the class still works by inspection:

```python
# aprsd/cmds/listen.py - NO CHANGES NEEDED
# APRSDListenProcessThread extends APRSDFilterThread which now uses:
#   queue.get(timeout=self.period) for interruptible wait
# The daemon=True default is inherited from base APRSDThread
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/ -v`
Expected: PASS

- [ ] **Step 5: Commit RX thread changes**

```bash
git add aprsd/threads/rx.py
git commit -m "refactor(threads): migrate RX threads to Event-based timing

- APRSDRXThread: use wait(timeout=5) for error recovery
- APRSDFilterThread: use queue.get(timeout=period) as interruptible wait
- APRSDListenProcessThread inherits changes from APRSDFilterThread
- Remove time.sleep() calls"
```

---

## Chunk 4: TX and Registry Thread Migration

### Task 6: Migrate TX Threads

**Files:**
- Modify: `aprsd/threads/tx.py`

- [ ] **Step 1: Update PacketSendSchedulerThread (non-daemon)**

```python
class PacketSendSchedulerThread(aprsd_threads.APRSDThread):
    """Scheduler thread that uses a threadpool to send packets."""

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

        for msg_no in list(pkt_tracker.keys()):
            packet = pkt_tracker.get(msg_no)
            if not packet:
                continue

            if isinstance(packet, core.AckPacket):
                continue

            if packet.send_count >= packet.retry_count:
                continue

            self.executor.submit(_send_packet_worker, msg_no)

        self.wait()  # Wait for period (1s) or shutdown signal
        return True

    def _cleanup(self):
        """Cleanup threadpool executor on thread shutdown."""
        LOG.debug('Shutting down PacketSendSchedulerThread executor')
        self.executor.shutdown(wait=True)
```

- [ ] **Step 2: Update AckSendSchedulerThread (non-daemon)**

```python
class AckSendSchedulerThread(aprsd_threads.APRSDThread):
    """Scheduler thread that uses a threadpool to send ack packets."""

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

        for msg_no in list(pkt_tracker.keys()):
            packet = pkt_tracker.get(msg_no)
            if not packet:
                continue

            if not isinstance(packet, core.AckPacket):
                continue

            if packet.send_count >= self.max_retries:
                continue

            self.executor.submit(_send_ack_worker, msg_no, self.max_retries)

        self.wait()  # Wait for period (1s) or shutdown signal
        return True

    def _cleanup(self):
        """Cleanup threadpool executor on thread shutdown."""
        LOG.debug('Shutting down AckSendSchedulerThread executor')
        self.executor.shutdown(wait=True)
```

- [ ] **Step 3: Update SendPacketThread**

```python
class SendPacketThread(aprsd_threads.APRSDThread):

    def __init__(self, packet):
        self.packet = packet
        super().__init__(f'TX-{packet.to_call}-{self.packet.msgNo}')

    def loop(self):
        """Loop until a message is acked or max retries reached."""
        pkt_tracker = tracker.PacketTrack()
        packet = pkt_tracker.get(self.packet.msgNo)
        if not packet:
            LOG.info(
                f'{self.packet.__class__.__name__}'
                f'({self.packet.msgNo}) '
                'Message Send Complete via Ack.',
            )
            return False

        send_now = False
        if packet.send_count >= packet.retry_count:
            LOG.info(
                f'{packet.__class__.__name__} '
                f'({packet.msgNo}) '
                'Message Send Complete. Max attempts reached'
                f' {packet.retry_count}',
            )
            pkt_tracker.remove(packet.msgNo)
            return False

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

        self.wait()  # Wait for period (1s) or shutdown signal
        return True
```

- [ ] **Step 4: Update SendAckThread**

```python
class SendAckThread(aprsd_threads.APRSDThread):
    max_retries = 3

    def __init__(self, packet):
        self.packet = packet
        super().__init__(f'TXAck-{packet.to_call}-{self.packet.msgNo}')
        self.max_retries = CONF.default_ack_send_count

    def loop(self):
        """Separate thread to send acks with retries."""
        send_now = False
        if self.packet.send_count == self.max_retries:
            LOG.debug(
                f'{self.packet.__class__.__name__}'
                f'({self.packet.msgNo}) '
                'Send Complete. Max attempts reached'
                f' {self.max_retries}',
            )
            return False

        if self.packet.last_send_time:
            now = int(round(time.time()))
            sleep_time = 31
            delta = now - self.packet.last_send_time
            if delta > sleep_time:
                send_now = True
        else:
            send_now = True

        if send_now:
            sent = False
            try:
                sent = _send_direct(self.packet)
            except Exception:
                LOG.error(f'Failed to send packet: {self.packet}')
            else:
                if sent:
                    self.packet.send_count += 1

            self.packet.last_send_time = int(round(time.time()))

        self.wait()  # Wait for period (1s) or shutdown signal
        return True
```

- [ ] **Step 5: Update BeaconSendThread**

```python
class BeaconSendThread(aprsd_threads.APRSDThread):
    """Thread that sends a GPS beacon packet periodically."""

    def __init__(self):
        super().__init__('BeaconSendThread')
        # Set period from config
        self.period = CONF.beacon_interval
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
        pkt = core.BeaconPacket(
            from_call=CONF.callsign,
            to_call='APRS',
            latitude=float(CONF.latitude),
            longitude=float(CONF.longitude),
            comment='APRSD GPS Beacon',
            symbol=CONF.beacon_symbol,
        )
        try:
            pkt.retry_count = 1
            send(pkt, direct=True)
        except Exception as e:
            LOG.error(f'Failed to send beacon: {e}')
            APRSDClient().reset()
            if self.wait(timeout=5):  # Interruptible error recovery wait
                return False

        self.wait()  # Wait for beacon_interval or shutdown signal
        return True
```

- [ ] **Step 6: Run tests**

Run: `pytest tests/ -v`
Expected: PASS

- [ ] **Step 7: Commit TX thread changes**

```bash
git add aprsd/threads/tx.py
git commit -m "refactor(threads): migrate TX threads to Event-based timing

- PacketSendSchedulerThread: daemon=False
- AckSendSchedulerThread: daemon=False
- SendPacketThread, SendAckThread, BeaconSendThread: daemon=True (default)
- BeaconSendThread: period from CONF.beacon_interval
- Replace time.sleep(1) with self.wait()
- Remove counter-based timing (_loop_cnt)"
```

---

### Task 7: Migrate APRSRegistryThread

**Files:**
- Modify: `aprsd/threads/registry.py`

- [ ] **Step 1: Update APRSRegistryThread**

```python
class APRSRegistryThread(aprsd_threads.APRSDThread):
    """This sends service information to the configured APRS Registry."""

    def __init__(self):
        super().__init__('APRSRegistryThread')
        # Set period from config
        self.period = CONF.aprs_registry.frequency_seconds
        if not CONF.aprs_registry.enabled:
            LOG.error('APRS Registry is not enabled.')
            LOG.error('APRS Registry thread is STOPPING.')
            self.stop()
        LOG.info(
            'APRS Registry thread is running and will send '
            f'info every {CONF.aprs_registry.frequency_seconds} seconds '
            f'to {CONF.aprs_registry.registry_url}.',
        )

    def loop(self):
        info = {
            'callsign': CONF.callsign,
            'owner_callsign': CONF.owner_callsign,
            'description': CONF.aprs_registry.description,
            'service_website': CONF.aprs_registry.service_website,
            'software': f'APRSD version {aprsd.__version__} '
            'https://github.com/craigerl/aprsd',
        }
        try:
            requests.post(
                f'{CONF.aprs_registry.registry_url}',
                json=info,
            )
        except Exception as e:
            LOG.error(f'Failed to send registry info: {e}')

        self.wait()  # Wait for frequency_seconds or shutdown signal
        return True
```

- [ ] **Step 2: Run tests**

Run: `pytest tests/ -v`
Expected: PASS

- [ ] **Step 3: Commit registry thread changes**

```bash
git add aprsd/threads/registry.py
git commit -m "refactor(threads): migrate APRSRegistryThread to Event-based timing

- Set period from CONF.aprs_registry.frequency_seconds
- Remove counter-based timing (_loop_cnt)
- Replace time.sleep(1) with self.wait()"
```

---

## Chunk 5: Signal Handler and Final Cleanup

### Task 8: Update Signal Handler

**Files:**
- Modify: `aprsd/main.py:76-97`

- [ ] **Step 1: Update signal_handler function**

```python
def signal_handler(sig, frame):
    click.echo('signal_handler: called')
    collector.Collector().stop_all()
    thread_list = threads.APRSDThreadList()
    thread_list.stop_all()

    if 'subprocess' not in str(frame):
        LOG.info(
            'Ctrl+C, Sending all threads exit! {}'.format(
                datetime.datetime.now(),
            ),
        )
        # Wait for non-daemon threads to finish gracefully
        thread_list.join_non_daemon(timeout=5.0)
        try:
            packets.PacketTrack().save()
            packets.WatchList().save()
            packets.SeenList().save()
            packets.PacketList().save()
            collector.Collector().collect()
        except Exception as e:
            LOG.error(f'Failed to save data: {e}')
            sys.exit(0)
```

- [ ] **Step 2: Run full test suite**

Run: `pytest tests/ -v`
Expected: PASS

- [ ] **Step 3: Commit signal handler changes**

```bash
git add aprsd/main.py
git commit -m "refactor(main): update signal handler for Event-based thread shutdown

- Replace time.sleep(1.5) with join_non_daemon(timeout=5.0)
- Non-daemon threads get graceful shutdown
- Daemon threads terminate immediately on exit"
```

---

### Task 9: Remove unused imports

**Files:**
- Modify: `aprsd/threads/keepalive.py`
- Modify: `aprsd/threads/stats.py`
- Modify: `aprsd/threads/rx.py`
- Modify: `aprsd/threads/tx.py`
- Modify: `aprsd/threads/registry.py`

- [ ] **Step 1: Remove `import time` where no longer needed**

Check each file and remove `import time` if `time.sleep` is no longer used. Keep it if `time.time()` is still used.

Files to check:
- `keepalive.py`: Remove `import time` (no longer used)
- `stats.py`: Keep `import time` (uses `time.time()`)
- `rx.py`: Remove `import time` (no longer used)
- `tx.py`: Keep `import time` (uses `time.time()`)
- `registry.py`: Remove `import time` (no longer used)

- [ ] **Step 2: Run linter**

Run: `tox -e lint`
Expected: PASS

- [ ] **Step 3: Run full test suite**

Run: `pytest tests/ -v`
Expected: PASS

- [ ] **Step 4: Commit cleanup**

```bash
git add aprsd/threads/keepalive.py aprsd/threads/rx.py aprsd/threads/registry.py
git commit -m "chore(threads): remove unused time imports"
```

---

### Task 10: Final Verification

- [ ] **Step 1: Run full test suite with coverage**

Run: `pytest tests/ --cov=aprsd -v`
Expected: PASS with good coverage

- [ ] **Step 2: Run type checking**

Run: `tox -e type-check`
Expected: PASS (or existing errors only)

- [ ] **Step 3: Manual smoke test**

Start the server briefly to verify threads start correctly:
```bash
aprsd server --help
```

- [ ] **Step 4: Create summary commit**

If any fixes were needed during verification, commit them.

---

## Summary

**Total Tasks:** 10
**Total Steps:** ~45

**Files Modified:**
- `aprsd/threads/aprsd.py` (base class + ThreadList)
- `aprsd/threads/keepalive.py`
- `aprsd/threads/stats.py`
- `aprsd/threads/rx.py`
- `aprsd/threads/tx.py`
- `aprsd/threads/registry.py`
- `aprsd/main.py`
- `tests/threads/test_aprsd_thread.py`

**Key Changes:**
1. Base class: `daemon`, `period` attributes, `_shutdown_event`, `wait()` method
2. Non-daemon threads: `PacketSendSchedulerThread`, `AckSendSchedulerThread`, `APRSDStatsStoreThread`
3. All counter-based timing replaced with period-based `wait()`
4. Signal handler uses `join_non_daemon()` instead of `sleep(1.5)`
