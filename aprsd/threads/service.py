# aprsd/aprsd/threads/service.py
#
# This module is used to register threads that the service command runs.
#
# The service command is used to start and stop the APRS service.
# This is a mechanism to register threads that the service or command
# needs to run, and then start stop them as needed.

from aprsd.threads import aprsd as aprsd_threads
from aprsd.utils import singleton


@singleton
class ServiceThreads:
    """Registry for threads that the service command runs.

    This enables extensions to register a thread to run during
    the service command.
    """

    def __init__(self):
        self.threads: list[aprsd_threads.APRSDThread] = []

    def register(self, thread: aprsd_threads.APRSDThread):
        if not isinstance(thread, aprsd_threads.APRSDThread):
            raise TypeError(f'Thread {thread} is not an APRSDThread')
        self.threads.append(thread)

    def unregister(self, thread: aprsd_threads.APRSDThread):
        if not isinstance(thread, aprsd_threads.APRSDThread):
            raise TypeError(f'Thread {thread} is not an APRSDThread')
        self.threads.remove(thread)

    def start(self):
        """Start all threads in the list."""
        for thread in self.threads:
            thread.start()

    def join(self):
        """Join all the threads in the list"""
        for thread in self.threads:
            thread.join()
