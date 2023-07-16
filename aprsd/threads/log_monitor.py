import logging
import threading

import wrapt

from aprsd import threads
from aprsd.log import log


LOG = logging.getLogger("APRSD")


class LogEntries:
    entries = []
    lock = threading.Lock()
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @wrapt.synchronized(lock)
    def add(self, entry):
        self.entries.append(entry)

    @wrapt.synchronized(lock)
    def get_all_and_purge(self):
        entries = self.entries.copy()
        self.entries = []
        return entries

    @wrapt.synchronized(lock)
    def __len__(self):
        return len(self.entries)


class LogMonitorThread(threads.APRSDThread):

    def __init__(self):
        super().__init__("LogMonitorThread")

    def loop(self):
        try:
            record = log.logging_queue.get(block=True, timeout=2)
            if isinstance(record, list):
                for item in record:
                    entry = self.json_record(item)
                    LogEntries().add(entry)
            else:
                entry = self.json_record(record)
                LogEntries().add(entry)
        except Exception:
            # Just ignore thi
            pass

        return True

    def json_record(self, record):
        entry = {}
        entry["filename"] = record.filename
        entry["funcName"] = record.funcName
        entry["levelname"] = record.levelname
        entry["lineno"] = record.lineno
        entry["module"] = record.module
        entry["name"] = record.name
        entry["pathname"] = record.pathname
        entry["process"] = record.process
        entry["processName"] = record.processName
        if hasattr(record, "stack_info"):
            entry["stack_info"] = record.stack_info
        else:
            entry["stack_info"] = None
        entry["thread"] = record.thread
        entry["threadName"] = record.threadName
        entry["message"] = record.getMessage()
        return entry
