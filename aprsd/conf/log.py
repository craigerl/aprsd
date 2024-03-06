"""
The options for log setup
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

DEFAULT_LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<yellow>{thread.name: <18}</yellow> | "
    "<level>{level: <8}</level> | "
    "<level>{message}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function:}</cyan>:<magenta>{line:}</magenta>"
)

logging_group = cfg.OptGroup(
    name="logging",
    title="Logging options",
)
logging_opts = [
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
    cfg.StrOpt(
        "log_level",
        default="INFO",
        choices=LOG_LEVELS.keys(),
        help="Log level for logging of events.",
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
