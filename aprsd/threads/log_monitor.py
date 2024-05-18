import datetime
import logging
import threading

from oslo_config import cfg
import requests
import wrapt

from aprsd import threads
from aprsd.log import log


CONF = cfg.CONF
LOG = logging.getLogger("APRSD")


def send_log_entries(force=False):
    """Send all of the log entries to the web interface."""
    if CONF.admin.web_enabled:
        if force or LogEntries().is_purge_ready():
            entries = LogEntries().get_all_and_purge()
            if entries:
                try:
                    requests.post(
                        f"http://{CONF.admin.web_ip}:{CONF.admin.web_port}/log_entries",
                        json=entries,
                        auth=(CONF.admin.user, CONF.admin.password),
                    )
                except Exception:
                    LOG.warning(f"Failed to send log entries. len={len(entries)}")


class LogEntries:
    entries = []
    lock = threading.Lock()
    _instance = None
    last_purge = datetime.datetime.now()
    max_delta = datetime.timedelta(
        hours=0.0, minutes=0, seconds=2,
    )

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def stats(self) -> dict:
        return {
            "log_entries": self.entries,
        }

    @wrapt.synchronized(lock)
    def add(self, entry):
        self.entries.append(entry)

    @wrapt.synchronized(lock)
    def get_all_and_purge(self):
        entries = self.entries.copy()
        self.entries = []
        self.last_purge = datetime.datetime.now()
        return entries

    def is_purge_ready(self):
        now = datetime.datetime.now()
        if (
            now - self.last_purge > self.max_delta
            and len(self.entries) > 1
        ):
            return True
        return False

    @wrapt.synchronized(lock)
    def __len__(self):
        return len(self.entries)


class LogMonitorThread(threads.APRSDThread):

    def __init__(self):
        super().__init__("LogMonitorThread")

    def stop(self):
        send_log_entries(force=True)
        super().stop()

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

        send_log_entries()
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
