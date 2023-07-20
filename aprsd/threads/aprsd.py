import abc
import datetime
import logging
import threading

import wrapt


LOG = logging.getLogger("APRSD")


class APRSDThreadList:
    """Singleton class that keeps track of application wide threads."""

    _instance = None

    threads_list = []
    lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls.threads_list = []
        return cls._instance

    @wrapt.synchronized(lock)
    def add(self, thread_obj):
        self.threads_list.append(thread_obj)

    @wrapt.synchronized(lock)
    def remove(self, thread_obj):
        self.threads_list.remove(thread_obj)

    @wrapt.synchronized(lock)
    def stop_all(self):
        """Iterate over all threads and call stop on them."""
        for th in self.threads_list:
            LOG.info(f"Stopping Thread {th.name}")
            if hasattr(th, "packet"):
                LOG.info(F"{th.name} packet {th.packet}")
            th.stop()

    @wrapt.synchronized(lock)
    def __len__(self):
        return len(self.threads_list)


class APRSDThread(threading.Thread, metaclass=abc.ABCMeta):

    def __init__(self, name):
        super().__init__(name=name)
        self.thread_stop = False
        APRSDThreadList().add(self)
        self._last_loop = datetime.datetime.now()

    def _should_quit(self):
        """ see if we have a quit message from the global queue."""
        if self.thread_stop:
            return True

    def stop(self):
        self.thread_stop = True

    @abc.abstractmethod
    def loop(self):
        pass

    def _cleanup(self):
        """Add code to subclass to do any cleanup"""

    def __str__(self):
        out = f"Thread <{self.__class__.__name__}({self.name}) Alive? {self.is_alive()}>"
        return out

    def loop_age(self):
        """How old is the last loop call?"""
        return datetime.datetime.now() - self._last_loop

    def run(self):
        LOG.debug("Starting")
        while not self._should_quit():
            can_loop = self.loop()
            self._last_loop = datetime.datetime.now()
            if not can_loop:
                self.stop()
        self._cleanup()
        APRSDThreadList().remove(self)
        LOG.debug("Exiting")
