"""
The options for log setup
"""

import logging

from oslo_config import cfg

LOG_LEVELS = {
    'CRITICAL': logging.CRITICAL,
    'ERROR': logging.ERROR,
    'WARNING': logging.WARNING,
    'INFO': logging.INFO,
    'DEBUG': logging.DEBUG,
}

DEFAULT_DATE_FORMAT = '%m/%d/%Y %I:%M:%S %p'

# Default log format parts
DEFAULT_LOG_FORMAT_TIMESTAMP = '<fg #008329>{time:YYYY-MM-DD HH:mm:ss.SSS}</>'
DEFAULT_LOG_FORMAT_THREAD = '<yellow>{thread.name: <18}</yellow>'
DEFAULT_LOG_FORMAT_LEVEL = '<level>{level: <8}</level>'
DEFAULT_LOG_FORMAT_MESSAGE = '<level>{message}</level>'
DEFAULT_LOG_FORMAT_LOCATION = (
    '<cyan>{name}</cyan>:<cyan>{function:}</cyan>:<magenta>{line:}</magenta>'
)

# Build default format from parts
DEFAULT_LOG_FORMAT = (
    f'{DEFAULT_LOG_FORMAT_TIMESTAMP} | '
    f'{DEFAULT_LOG_FORMAT_THREAD} | '
    f'{DEFAULT_LOG_FORMAT_LEVEL} | '
    f'{DEFAULT_LOG_FORMAT_MESSAGE} | '
    f'{DEFAULT_LOG_FORMAT_LOCATION}'
)

logging_group = cfg.OptGroup(
    name='logging',
    title='Logging options',
)
logging_opts = [
    cfg.StrOpt(
        'logfile',
        default=None,
        help='File to log to',
    ),
    cfg.StrOpt(
        'logformat',
        default=DEFAULT_LOG_FORMAT,
        help='Log file format, unless rich_logging enabled.',
    ),
    cfg.StrOpt(
        'log_level',
        default='INFO',
        choices=LOG_LEVELS.keys(),
        help='Log level for logging of events.',
    ),
    cfg.BoolOpt(
        'enable_color',
        default=True,
        help='Enable ANSI color codes in logging',
    ),
    cfg.BoolOpt(
        'enable_console_stdout',
        default=True,
        help='Enable logging to the console/stdout.',
    ),
]


def register_opts(config):
    config.register_group(logging_group)
    config.register_opts(logging_opts, group=logging_group)


def list_opts():
    return {
        logging_group.name: (logging_opts),
    }
