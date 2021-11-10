import logging
from logging import NullHandler
from logging.handlers import RotatingFileHandler
import queue
import sys

from aprsd import config as aprsd_config


LOG = logging.getLogger("APRSD")
logging_queue = queue.Queue()


# Setup the logging faciility
# to disable logging to stdout, but still log to file
# use the --quiet option on the cmdln
def setup_logging(config, loglevel, quiet):
    log_level = aprsd_config.LOG_LEVELS[loglevel]
    LOG.setLevel(log_level)
    log_format = config["aprsd"].get("logformat", aprsd_config.DEFAULT_LOG_FORMAT)
    date_format = config["aprsd"].get("dateformat", aprsd_config.DEFAULT_DATE_FORMAT)
    log_formatter = logging.Formatter(fmt=log_format, datefmt=date_format)
    log_file = config["aprsd"].get("logfile", None)
    if log_file:
        fh = RotatingFileHandler(log_file, maxBytes=(10248576 * 5), backupCount=4)
    else:
        fh = NullHandler()

    fh.setFormatter(log_formatter)
    LOG.addHandler(fh)

    imap_logger = None
    if config.get("aprsd.email.enabled", default=False) and config.get("aprsd.email.imap.debug", default=False):

        imap_logger = logging.getLogger("imapclient.imaplib")
        imap_logger.setLevel(log_level)
        imap_logger.addHandler(fh)

    if config.get("aprsd.web.enabled", default=False):
        qh = logging.handlers.QueueHandler(logging_queue)
        q_log_formatter = logging.Formatter(
            fmt=aprsd_config.QUEUE_LOG_FORMAT,
            datefmt=aprsd_config.QUEUE_DATE_FORMAT,
        )
        qh.setFormatter(q_log_formatter)
        LOG.addHandler(qh)

    if not quiet:
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
