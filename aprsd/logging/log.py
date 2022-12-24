import logging
from logging import NullHandler
from logging.handlers import RotatingFileHandler
import queue
import sys

from oslo_config import cfg

from aprsd import config as aprsd_config
from aprsd.logging import rich as aprsd_logging


CONF = cfg.CONF
LOG = logging.getLogger("APRSD")
logging_queue = queue.Queue()


# Setup the logging faciility
# to disable logging to stdout, but still log to file
# use the --quiet option on the cmdln
def setup_logging(loglevel, quiet):
    log_level = aprsd_config.LOG_LEVELS[loglevel]
    LOG.setLevel(log_level)
    date_format = CONF.logging.get("date_format", aprsd_config.DEFAULT_DATE_FORMAT)
    rh = None
    fh = None

    rich_logging = False
    if CONF.logging.get("rich_logging", False) and not quiet:
        log_format = "%(message)s"
        log_formatter = logging.Formatter(fmt=log_format, datefmt=date_format)
        rh = aprsd_logging.APRSDRichHandler(
            show_thread=True, thread_width=20,
            rich_tracebacks=True, omit_repeated_times=False,
        )
        rh.setFormatter(log_formatter)
        LOG.addHandler(rh)
        rich_logging = True

    log_file = CONF.logging.logfile
    log_format = CONF.logging.logformat
    log_formatter = logging.Formatter(fmt=log_format, datefmt=date_format)

    if log_file:
        fh = RotatingFileHandler(log_file, maxBytes=(10248576 * 5), backupCount=4)
        fh.setFormatter(log_formatter)
        LOG.addHandler(fh)

    imap_logger = None
    if CONF.email_plugin.enabled and CONF.email_plugin.debug:
        imap_logger = logging.getLogger("imapclient.imaplib")
        imap_logger.setLevel(log_level)
        if rh:
          imap_logger.addHandler(rh)
        if fh:
            imap_logger.addHandler(fh)


    if CONF.admin.get("web_enabled", default=False):
        qh = logging.handlers.QueueHandler(logging_queue)
        q_log_formatter = logging.Formatter(
            fmt=aprsd_config.QUEUE_LOG_FORMAT,
            datefmt=aprsd_config.QUEUE_DATE_FORMAT,
        )
        qh.setFormatter(q_log_formatter)
        LOG.addHandler(qh)

    if not quiet and not rich_logging:
        sh = logging.StreamHandler(sys.stdout)
        sh.setFormatter(log_formatter)
        LOG.addHandler(sh)
        if imap_logger:
            imap_logger.addHandler(sh)


def setup_logging_no_config(loglevel, quiet):
    log_level = aprsd_config.LOG_LEVELS[loglevel]
    LOG.setLevel(log_level)
    log_format = aprsd_config.DEFAULT_LOG_FORMAT
    date_format = aprsd_config.DEFAULT_DATE_FORMAT
    log_formatter = logging.Formatter(fmt=log_format, datefmt=date_format)
    fh = NullHandler()

    fh.setFormatter(log_formatter)
    LOG.addHandler(fh)

    if not quiet:
        sh = logging.StreamHandler(sys.stdout)
        sh.setFormatter(log_formatter)
        LOG.addHandler(sh)
