"""
The options for logging setup
"""
import logging

from oslo_config import cfg


LOG_LEVELS = {
    "CRITICAL": logging.CRITICAL,
    "ERROR": logging.ERROR,
    "WARNING": logging.WARNING,
    "INFO": logging.INFO,
    "DEBUG": logging.DEBUG,
}

DEFAULT_DATE_FORMAT = "%m/%d/%Y %I:%M:%S %p"
DEFAULT_LOG_FORMAT = (
    "[%(asctime)s] [%(threadName)-20.20s] [%(levelname)-5.5s]"
    " %(message)s - [%(pathname)s:%(lineno)d]"
)

logging_group = cfg.OptGroup(
    name="logging",
    title="Logging options",
)
logging_opts = [
    cfg.StrOpt(
        "date_format",
        default=DEFAULT_DATE_FORMAT,
        help="Date format for log entries",
    ),
    cfg.BoolOpt(
        "rich_logging",
        default=True,
        help="Enable Rich logging",
    ),
    cfg.StrOpt(
        "logfile",
        default=None,
        help="File to log to",
    ),
    cfg.StrOpt(
        "logformat",
        default=DEFAULT_LOG_FORMAT,
        help="Log file format, unless rich_logging enabled.",
    ),
]


def register_opts(config):
    config.register_group(logging_group)
    config.register_opts(logging_opts, group=logging_group)


def list_opts():
    return {
        logging_group.name: (
            logging_opts
        ),
    }
