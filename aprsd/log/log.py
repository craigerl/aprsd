import logging
from logging.handlers import QueueHandler
import queue
import sys

from loguru import logger
from oslo_config import cfg

from aprsd.conf import log as conf_log


CONF = cfg.CONF
# LOG = logging.getLogger("APRSD")
LOG = logger


class QueueLatest(queue.Queue):
    """Custom Queue to keep only the latest N items.

    This prevents the queue from blowing up in size.
    """
    def put(self, *args, **kwargs):
        try:
            super().put(*args, **kwargs)
        except queue.Full:
            self.queue.popleft()
            super().put(*args, **kwargs)


logging_queue = QueueLatest(maxsize=200)


class InterceptHandler(logging.Handler):
    def emit(self, record):
        # get corresponding Loguru level if it exists
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # find caller from where originated the logged message
        frame, depth = sys._getframe(6), 6
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


# Setup the log faciility
# to disable log to stdout, but still log to file
# use the --quiet option on the cmdln
def setup_logging(loglevel=None, quiet=False):
    if not loglevel:
        log_level = CONF.logging.log_level
    else:
        log_level = conf_log.LOG_LEVELS[loglevel]

    # intercept everything at the root logger
    logging.root.handlers = [InterceptHandler()]
    logging.root.setLevel(log_level)

    imap_list = [
        "imapclient.imaplib", "imaplib", "imapclient",
        "imapclient.util",
    ]
    aprslib_list = [
        "aprslib",
        "aprslib.parsing",
        "aprslib.exceptions",
    ]
    webserver_list = [
        "werkzeug",
        "werkzeug._internal",
        "socketio",
        "urllib3.connectionpool",
        "chardet",
        "chardet.charsetgroupprober",
        "chardet.eucjpprober",
        "chardet.mbcharsetprober",
    ]

    # We don't really want to see the aprslib parsing debug output.
    disable_list = imap_list + aprslib_list + webserver_list

    # remove every other logger's handlers
    # and propagate to root logger
    for name in logging.root.manager.loggerDict.keys():
        logging.getLogger(name).handlers = []
        if name in disable_list:
            logging.getLogger(name).propagate = False
        else:
            logging.getLogger(name).propagate = True

    if CONF.webchat.disable_url_request_logging:
        for name in webserver_list:
            logging.getLogger(name).handlers = []
            logging.getLogger(name).propagate = True
            logging.getLogger(name).setLevel(logging.ERROR)

    handlers = [
        {
            "sink": sys.stdout,
            "serialize": False,
            "format": CONF.logging.logformat,
            "colorize": True,
            "level": log_level,
        },
    ]
    if CONF.logging.logfile:
        handlers.append(
            {
                "sink": CONF.logging.logfile,
                "serialize": False,
                "format": CONF.logging.logformat,
                "colorize": False,
                "level": log_level,
            },
        )

    if CONF.email_plugin.enabled and CONF.email_plugin.debug:
        for name in imap_list:
            logging.getLogger(name).propagate = True

    if CONF.admin.web_enabled:
        qh = QueueHandler(logging_queue)
        handlers.append(
            {
                "sink": qh, "serialize": False,
                "format": CONF.logging.logformat,
                "level": log_level,
                "colorize": False,
            },
        )

    # configure loguru
    logger.configure(handlers=handlers)
    logger.level("DEBUG", color="<fg #BABABA>")
