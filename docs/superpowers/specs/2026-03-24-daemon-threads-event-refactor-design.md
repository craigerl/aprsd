# Daemon Threads and Event-Based Timing Refactor

**Date:** 2026-03-24
**Status:** Draft
**Scope:** All APRSD thread classes

## Overview

Refactor all APRSD thread classes to use daemon threads and replace counter-based sleep patterns with `threading.Event()` for interruptible waits and cleaner periodic timing.

## Goals

1. **Faster shutdown** — threads respond to shutdown signals immediately instead of waiting for `time.sleep()` to complete
2. **Cleaner periodic timing** — replace counter-based timing (`loop_count % 60`) with explicit period-based waits
3. **Proper daemon semantics** — most threads become daemon threads; critical I/O threads remain non-daemon for graceful shutdown

## Current State

- **14 thread classes** extend `APRSDThread` base class
- All use `time.sleep(1)` with counter-based conditionals for periodic work
- Shutdown via boolean `thread_stop` flag, polled in while loop
- No threads set as daemon — all block program exit
- No `threading.Event()` usage anywhere

### Current Problems

1. Shutdown delay: up to 1-5 seconds waiting for sleep to finish
2. Counter math is fragile and obscures intent
3. Non-daemon threads prevent clean program exit

## Design

### Base Class Changes

File: `aprsd/threads/aprsd.py`

```python
class APRSDThread(threading.Thread, metaclass=abc.ABCMeta):
    # Class attributes (subclasses override as needed)
    daemon = True           # Most threads are daemon
    period = 1              # Default wait period in seconds

    def __init__(self, name):
        super().__init__(name=name)
        self.daemon = self.__class__.daemon
        self._shutdown_event = threading.Event()
        self.loop_count = 0  # Retained for debugging
        self._last_loop = datetime.datetime.now()
        APRSDThreadList().add(self)

    def _should_quit(self) -> bool:
        """Check if thread should exit."""
        return self._shutdown_event.is_set()

    def stop(self):
        """Signal thread to stop. Returns immediately."""
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

    def run(self):
        while not self._should_quit():
            self.loop_count += 1
            self._last_loop = datetime.datetime.now()
            if not self.loop():
                break
        APRSDThreadList().remove(self)
```

### Daemon vs Non-Daemon Threads

**Non-daemon threads (3)** — require graceful shutdown for I/O operations:

| Thread | File | Reason |
|--------|------|--------|
| `PacketSendSchedulerThread` | tx.py | Manages packet send queue |
| `AckSendSchedulerThread` | tx.py | Manages ACK send queue |
| `APRSDStatsStoreThread` | stats.py | Writes stats to disk |

**Daemon threads (12)** — can be terminated immediately:

- `APRSDRXThread`, `APRSDFilterThread`, `APRSDProcessPacketThread`, `APRSDPluginProcessPacketThread`
- `APRSDPushStatsThread`, `StatsLogThread`
- `KeepAliveThread`, `APRSRegistryThread`
- `SendPacketThread`, `SendAckThread`, `BeaconSendThread`
- `APRSDListenProcessThread` (listen command)

### Subclass Migration Pattern

**Before:**
```python
class KeepAliveThread(APRSDThread):
    def loop(self):
        if self.loop_count % 60 == 0:
            self._do_keepalive_work()
        time.sleep(1)
        return True
```

**After:**
```python
class KeepAliveThread(APRSDThread):
    period = 60

    def loop(self):
        self._do_keepalive_work()
        self.wait()
        return True
```

### Thread Periods

| Thread | New `period` | Source |
|--------|--------------|--------|
| `KeepAliveThread` | 60 | Fixed |
| `APRSDStatsStoreThread` | 10 | Fixed |
| `APRSDPushStatsThread` | config | `CONF.push_stats.period` |
| `StatsLogThread` | 10 | Fixed |
| `APRSRegistryThread` | config | `CONF.aprs_registry.frequency_seconds` |
| `BeaconSendThread` | config | `CONF.beacon_interval` |
| `APRSDRXThread` | 1 | Default |
| `APRSDFilterThread` | 1 | Default |
| `APRSDProcessPacketThread` | 1 | Default |
| `APRSDPluginProcessPacketThread` | 1 | Default |
| `SendPacketThread` | 1 | Default |
| `SendAckThread` | 1 | Default |
| `PacketSendSchedulerThread` | 1 | Default |
| `AckSendSchedulerThread` | 1 | Default |
| `APRSDListenProcessThread` | 1 | Default |

Config-based periods are set in `__init__` or `setup()`. Note: `setup()` is called by subclasses in their `__init__` before the thread starts; the base class does not call it automatically.
```python
class APRSRegistryThread(APRSDThread):
    period = 1  # Default

    def setup(self):
        self.period = CONF.aprs_registry.frequency_seconds
```

### ThreadList Changes

File: `aprsd/threads/aprsd.py`

```python
class APRSDThreadList:
    def stop_all(self):
        """Signal all threads to stop."""
        with self.lock:
            for th in self.threads_list:
                th.stop()

    def join_non_daemon(self, timeout: float = 5.0):
        """Wait for non-daemon threads to complete gracefully."""
        with self.lock:
            for th in self.threads_list:
                if not th.daemon and th.is_alive():
                    th.join(timeout=timeout)
```

### Shutdown Handler Changes

File: `aprsd/main.py`

```python
def signal_handler(sig, frame):
    LOG.info("Shutdown signal received")
    thread_list = threads.APRSDThreadList()
    thread_list.stop_all()
    thread_list.join_non_daemon(timeout=5.0)
    # Daemon threads killed automatically on exit
```

### Queue-Based Threads

Threads that block on queues use queue timeout as interruptible wait:

```python
class APRSDFilterThread(APRSDThread):
    period = 1

    def loop(self):
        try:
            packet = self.queue.get(timeout=self.period)
            self._process(packet)
        except queue.Empty:
            pass  # Timeout, loop checks _should_quit
        return True
```

### Error Recovery Waits

Threads needing longer waits for error recovery use explicit timeout:

```python
class APRSDRXThread(APRSDThread):
    period = 1

    def loop(self):
        try:
            self._process_packets()
        except ConnectionError:
            LOG.error("Connection lost, retrying in 5s")
            if self.wait(timeout=5):
                return False  # Shutdown signaled
        self.wait()
        return True
```

## Files to Modify

1. `aprsd/threads/aprsd.py` — Base class and ThreadList
2. `aprsd/threads/rx.py` — RX thread classes (4)
3. `aprsd/threads/tx.py` — TX thread classes (5)
4. `aprsd/threads/stats.py` — Stats thread classes (3)
5. `aprsd/threads/keepalive.py` — KeepAliveThread
6. `aprsd/threads/registry.py` — APRSRegistryThread
7. `aprsd/main.py` — Signal handler
8. `aprsd/cmds/listen.py` — APRSDListenProcessThread

## Testing Strategy

1. **Unit tests for base class:**
   - `wait()` returns `True` immediately when event is already set
   - `wait(timeout=5)` returns `False` after 5 seconds if event not set
   - `stop()` causes `_should_quit()` to return `True`
   - `daemon` attribute is set correctly from class attribute

2. **Integration tests:**
   - Shutdown completes in <1s for daemon-only scenarios
   - Non-daemon threads get up to 5s grace period
   - `join_non_daemon()` respects timeout parameter

3. **Manual testing:**
   - Send SIGINT during operation, verify clean exit
   - Verify no "thread still running" warnings on shutdown

4. **Existing test updates:**
   - Update any tests that mock `thread_stop` to mock `_shutdown_event` instead
   - Update tests that check `time.sleep` calls to check `wait()` calls

## Backwards Compatibility

- `loop_count` retained for debugging/logging
- `_should_quit()` method signature unchanged
- Default `period=1` matches current 1-second sleep behavior

## Rollout

Single PR with all changes — the refactor is atomic and affects thread behavior globally.
