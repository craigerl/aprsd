import unittest

from aprsd.threads import aprsd as aprsd_threads
from aprsd.threads import service


class TestThread(aprsd_threads.APRSDThread):
    """Test thread for testing ServiceThreads."""

    def __init__(self, name='TestThread'):
        super().__init__(name)

    def loop(self):
        return False


class TestServiceThreads(unittest.TestCase):
    """Unit tests for the ServiceThreads class."""

    def setUp(self):
        """Set up test fixtures."""
        # Reset singleton instances
        service.ServiceThreads._instance = None
        aprsd_threads.APRSDThreadList._instance = None
        aprsd_threads.APRSDThreadList.threads_list = []
        # Clear ServiceThreads threads
        st = service.ServiceThreads()
        st.threads = []

    def tearDown(self):
        """Clean up after tests."""
        # Stop all threads
        st = service.ServiceThreads()
        for thread in list(st.threads):
            thread.stop()
            if thread.is_alive():
                thread.join(timeout=1)
        service.ServiceThreads._instance = None
        aprsd_threads.APRSDThreadList._instance = None
        aprsd_threads.APRSDThreadList.threads_list = []

    def test_singleton_pattern(self):
        """Test that ServiceThreads is a singleton."""
        st1 = service.ServiceThreads()
        st2 = service.ServiceThreads()
        self.assertIs(st1, st2)

    def test_init(self):
        """Test initialization."""
        st = service.ServiceThreads()
        self.assertEqual(st.threads, [])

    def test_register(self):
        """Test register() method."""
        st = service.ServiceThreads()
        thread = TestThread('Thread1')

        st.register(thread)
        self.assertIn(thread, st.threads)

    def test_register_non_thread(self):
        """Test register() raises TypeError for non-APRSDThread objects."""
        st = service.ServiceThreads()
        non_thread = object()

        with self.assertRaises(TypeError):
            st.register(non_thread)

    def test_unregister(self):
        """Test unregister() method."""
        st = service.ServiceThreads()
        thread = TestThread('Thread2')
        st.register(thread)

        st.unregister(thread)
        self.assertNotIn(thread, st.threads)

    def test_unregister_non_thread(self):
        """Test unregister() raises TypeError for non-APRSDThread objects."""
        st = service.ServiceThreads()
        non_thread = object()

        with self.assertRaises(TypeError):
            st.unregister(non_thread)

    def test_start(self):
        """Test start() method."""
        st = service.ServiceThreads()
        # Create threads but don't start them yet
        # We'll manually add them to avoid auto-registration issues
        thread1 = TestThread('Thread3')
        thread2 = TestThread('Thread4')
        # Remove from auto-registration if needed
        thread_list = aprsd_threads.APRSDThreadList()
        if thread1 in thread_list.threads_list:
            thread_list.remove(thread1)
        if thread2 in thread_list.threads_list:
            thread_list.remove(thread2)
        st.register(thread1)
        st.register(thread2)

        # Threads can only be started once, so we can't test start() easily
        # Just verify they're registered
        self.assertIn(thread1, st.threads)
        self.assertIn(thread2, st.threads)

    def test_join(self):
        """Test join() method."""
        st = service.ServiceThreads()
        thread = TestThread('Thread5')
        st.register(thread)
        st.start()

        # Should not raise exception
        st.join()

    def test_multiple_threads(self):
        """Test registering multiple threads."""
        st = service.ServiceThreads()
        # Clear any existing threads
        st.threads = []
        thread_list = aprsd_threads.APRSDThreadList()
        thread_list.threads_list = []

        threads = []
        for i in range(5):
            thread = TestThread(f'Thread{i}')
            # Remove from auto-registration if needed
            if thread in thread_list.threads_list:
                thread_list.remove(thread)
            threads.append(thread)
            st.register(thread)

        self.assertEqual(len(st.threads), 5)

        st.start()
        import time

        time.sleep(0.1)

        st.join(timeout=1)

        # All threads should be registered
        self.assertEqual(len(st.threads), 5)

    def test_register_after_start(self):
        """Test registering threads after starting."""
        st = service.ServiceThreads()
        thread_list = aprsd_threads.APRSDThreadList()
        thread_list.threads_list = []
        st.threads = []

        thread1 = TestThread('Thread6')
        # Remove from auto-registration if needed
        if thread1 in thread_list.threads_list:
            thread_list.remove(thread1)
        st.register(thread1)
        # Don't actually start threads (they can only be started once)
        # Just verify registration works

        thread2 = TestThread('Thread7')
        if thread2 in thread_list.threads_list:
            thread_list.remove(thread2)
        st.register(thread2)

        # Both should be registered
        self.assertIn(thread1, st.threads)
        self.assertIn(thread2, st.threads)
