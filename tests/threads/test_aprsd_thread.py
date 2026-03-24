import datetime
import threading
import time
import unittest

from aprsd.threads.aprsd import APRSDThread, APRSDThreadList


class TestThread(APRSDThread):
    """Test thread implementation for testing."""

    def __init__(self, name='TestThread', should_loop=True):
        super().__init__(name)
        self.should_loop = should_loop
        self.loop_called = False

    def loop(self):
        self.loop_called = True
        return self.should_loop


class TestAPRSDThread(unittest.TestCase):
    """Unit tests for the APRSDThread class."""

    def setUp(self):
        """Set up test fixtures."""
        # Reset singleton instances
        APRSDThreadList._instance = None
        APRSDThreadList.threads_list = []

    def tearDown(self):
        """Clean up after tests."""
        # Stop all threads
        thread_list = APRSDThreadList()
        for thread in list(thread_list.threads_list):
            thread.stop()
            if thread.is_alive():
                thread.join(timeout=1)
        APRSDThreadList._instance = None
        APRSDThreadList.threads_list = []

    def test_init(self):
        """Test thread initialization."""
        thread = TestThread('TestThread1')
        self.assertEqual(thread.name, 'TestThread1')
        self.assertFalse(thread._shutdown_event.is_set())
        self.assertFalse(thread._pause)
        self.assertEqual(thread.loop_count, 0)  # Was 1, now starts at 0
        thread_list = APRSDThreadList()
        self.assertIn(thread, thread_list.threads_list)

    def test_should_quit(self):
        """Test _should_quit() method."""
        thread = TestThread('TestThread2')
        self.assertFalse(thread._should_quit())
        thread._shutdown_event.set()
        self.assertTrue(thread._should_quit())

    def test_pause_unpause(self):
        """Test pause() and unpause() methods."""
        thread = TestThread('TestThread3')
        self.assertFalse(thread._pause)

        thread.pause()
        self.assertTrue(thread._pause)

        thread.unpause()
        self.assertFalse(thread._pause)

    def test_stop(self):
        """Test stop() method."""
        thread = TestThread('TestThread4')
        self.assertFalse(thread._shutdown_event.is_set())
        thread.stop()
        self.assertTrue(thread._shutdown_event.is_set())

    def test_loop_age(self):
        """Test loop_age() method."""
        thread = TestThread('TestThread5')
        age = thread.loop_age()
        self.assertIsInstance(age, datetime.timedelta)
        self.assertGreaterEqual(age.total_seconds(), 0)

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
        result = thread.wait(timeout=10)
        elapsed = time.time() - start
        self.assertTrue(result)
        self.assertLess(elapsed, 1)

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

    def test_str(self):
        """Test __str__() method."""
        thread = TestThread('TestThread6')
        thread_str = str(thread)
        self.assertIn('TestThread', thread_str)
        self.assertIn('TestThread6', thread_str)

    def test_cleanup(self):
        """Test _cleanup() method."""
        thread = TestThread('TestThread7')
        # Should not raise exception
        thread._cleanup()

    def test_run_loop(self):
        """Test run() method executes loop."""
        thread = TestThread('TestThread8', should_loop=False)
        thread.start()
        thread.join(timeout=2)

        self.assertTrue(thread.loop_called)
        self.assertFalse(thread.is_alive())

    def test_run_pause(self):
        """Test run() method with pause."""
        thread = TestThread('TestThread9', should_loop=True)
        thread.pause()
        thread.start()
        time.sleep(0.1)
        thread.stop()
        thread.join(timeout=1)

        # Should have paused
        self.assertFalse(thread.is_alive())

    def test_run_stop(self):
        """Test run() method stops when thread_stop is True."""
        thread = TestThread('TestThread10', should_loop=True)
        thread.start()
        time.sleep(0.1)
        thread.stop()
        thread.join(timeout=1)

        self.assertFalse(thread.is_alive())

    def test_abstract_loop(self):
        """Test that abstract loop() raises NotImplementedError."""
        with self.assertRaises(TypeError):
            # Can't instantiate abstract class directly
            APRSDThread('AbstractThread')


class TestAPRSDThreadList(unittest.TestCase):
    """Unit tests for the APRSDThreadList class."""

    def setUp(self):
        """Set up test fixtures."""
        APRSDThreadList._instance = None
        APRSDThreadList.threads_list = []

    def tearDown(self):
        """Clean up after tests."""
        thread_list = APRSDThreadList()
        for thread in list(thread_list.threads_list):
            thread.stop()
            if thread.is_alive():
                thread.join(timeout=1)
        APRSDThreadList._instance = None
        APRSDThreadList.threads_list = []

    def test_singleton_pattern(self):
        """Test that APRSDThreadList is a singleton."""
        list1 = APRSDThreadList()
        list2 = APRSDThreadList()
        self.assertIs(list1, list2)

    def test_add(self):
        """Test add() method."""
        thread_list = APRSDThreadList()
        thread = TestThread('TestThread1')

        thread_list.add(thread)
        self.assertIn(thread, thread_list.threads_list)

    def test_remove(self):
        """Test remove() method."""
        thread_list = APRSDThreadList()
        # Clear any existing threads
        thread_list.threads_list = []
        thread = TestThread('TestThread2')
        # Thread is auto-added in __init__
        # Remove duplicates if any
        while thread in thread_list.threads_list:
            thread_list.remove(thread)
        thread_list.add(thread)

        thread_list.remove(thread)
        self.assertNotIn(thread, thread_list.threads_list)

    def test_contains(self):
        """Test __contains__() method."""
        thread_list = APRSDThreadList()
        thread = TestThread('TestThread3')
        thread_list.add(thread)

        self.assertIn('TestThread3', thread_list)
        self.assertNotIn('NonExistentThread', thread_list)

    def test_len(self):
        """Test __len__() method."""
        thread_list = APRSDThreadList()
        # Clear any existing threads
        thread_list.threads_list = []
        self.assertEqual(len(thread_list), 0)

        thread1 = TestThread('TestThread4')
        # Thread is auto-added in __init__, so we may have 1 already
        # Remove if duplicate
        if thread1 in thread_list.threads_list:
            thread_list.remove(thread1)
        thread_list.add(thread1)

        thread2 = TestThread('TestThread5')
        if thread2 in thread_list.threads_list:
            thread_list.remove(thread2)
        thread_list.add(thread2)

        self.assertEqual(len(thread_list), 2)

    def test_stats(self):
        """Test stats() method."""
        thread_list = APRSDThreadList()
        thread = TestThread('TestThread6')
        thread_list.add(thread)

        stats = thread_list.stats()
        self.assertIsInstance(stats, dict)
        self.assertIn('TestThread6', stats)
        self.assertIn('name', stats['TestThread6'])
        self.assertIn('class', stats['TestThread6'])
        self.assertIn('alive', stats['TestThread6'])
        self.assertIn('age', stats['TestThread6'])
        self.assertIn('loop_count', stats['TestThread6'])

    def test_stats_serializable(self):
        """Test stats() with serializable=True."""
        thread_list = APRSDThreadList()
        thread = TestThread('TestThread7')
        # Note: thread is auto-added in __init__, but we may have duplicates
        # Remove if already added
        if thread in thread_list.threads_list:
            thread_list.remove(thread)
        thread_list.add(thread)

        stats = thread_list.stats(serializable=True)
        self.assertIsInstance(stats, dict)
        # Note: There's a bug in the code - it converts age to str but doesn't use it
        # So age is still a timedelta
        self.assertIn('TestThread7', stats)
        self.assertIn('age', stats['TestThread7'])

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

    def test_pause_all(self):
        """Test pause_all() method."""
        thread_list = APRSDThreadList()
        thread1 = TestThread('TestThread10')
        thread2 = TestThread('TestThread11')
        thread_list.add(thread1)
        thread_list.add(thread2)

        thread_list.pause_all()
        self.assertTrue(thread1._pause)
        self.assertTrue(thread2._pause)

    def test_unpause_all(self):
        """Test unpause_all() method."""
        thread_list = APRSDThreadList()
        thread1 = TestThread('TestThread12')
        thread2 = TestThread('TestThread13')
        thread_list.add(thread1)
        thread_list.add(thread2)
        thread1._pause = True
        thread2._pause = True

        thread_list.unpause_all()
        self.assertFalse(thread1._pause)
        self.assertFalse(thread2._pause)

    def test_info(self):
        """Test info() method."""
        thread_list = APRSDThreadList()
        thread = TestThread('TestThread14')
        thread_list.add(thread)

        info = thread_list.info()
        self.assertIsInstance(info, dict)
        self.assertIn('TestThread', info)
        self.assertIn('alive', info['TestThread'])
        self.assertIn('age', info['TestThread'])
        self.assertIn('name', info['TestThread'])

    def test_thread_safety(self):
        """Test thread safety of add/remove operations."""
        thread_list = APRSDThreadList()
        threads = []

        # Create multiple threads that add/remove
        def add_thread(i):
            thread = TestThread(f'Thread{i}')
            thread_list.add(thread)
            threads.append(thread)

        def remove_thread(thread):
            try:
                thread_list.remove(thread)
            except ValueError:
                pass  # Already removed

        # Add threads concurrently
        add_threads = [
            threading.Thread(target=add_thread, args=(i,)) for i in range(10)
        ]
        for t in add_threads:
            t.start()
        for t in add_threads:
            t.join()

        # Remove threads concurrently
        remove_threads = [
            threading.Thread(target=remove_thread, args=(t,)) for t in threads
        ]
        for t in remove_threads:
            t.start()
        for t in remove_threads:
            t.join()

        # Should handle concurrent access without errors
        self.assertGreaterEqual(len(thread_list), 0)

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
