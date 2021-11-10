from functools import update_wrapper
import typing as t

import click

from aprsd import config as aprsd_config
from aprsd import log


F = t.TypeVar("F", bound=t.Callable[..., t.Any])

common_options = [
    click.option(
        "--loglevel",
        default="INFO",
        show_default=True,
        type=click.Choice(
            ["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
            case_sensitive=False,
        ),
        show_choices=True,
        help="The log level to use for aprsd.log",
    ),
    click.option(
        "-c",
        "--config",
        "config_file",
        show_default=True,
        default=aprsd_config.DEFAULT_CONFIG_FILE,
        help="The aprsd config file to use for options.",
    ),
    click.option(
        "--quiet",
        is_flag=True,
        default=False,
        help="Don't log to stdout",
    ),
]


def add_options(options):
    def _add_options(func):
        for option in reversed(options):
            func = option(func)
        return func
    return _add_options


def process_standard_options(f: F) -> F:
    def new_func(*args, **kwargs):
        ctx = args[0]
        ctx.ensure_object(dict)
        ctx.obj["loglevel"] = kwargs["loglevel"]
        ctx.obj["config_file"] = kwargs["config_file"]
        ctx.obj["quiet"] = kwargs["quiet"]
        ctx.obj["config"] = aprsd_config.parse_config(kwargs["config_file"])
        log.setup_logging(
            ctx.obj["config"], ctx.obj["loglevel"],
            ctx.obj["quiet"],
        )

        del kwargs["loglevel"]
        del kwargs["config_file"]
        del kwargs["quiet"]
        return f(*args, **kwargs)

    return update_wrapper(t.cast(F, new_func), f)


def process_standard_options_no_config(f: F) -> F:
    """Use this as a decorator when config isn't needed."""
    def new_func(*args, **kwargs):
        ctx = args[0]
        ctx.ensure_object(dict)
        ctx.obj["loglevel"] = kwargs["loglevel"]
        ctx.obj["config_file"] = kwargs["config_file"]
        ctx.obj["quiet"] = kwargs["quiet"]
        log.setup_logging_no_config(
            ctx.obj["loglevel"],
            ctx.obj["quiet"],
        )

        del kwargs["loglevel"]
        del kwargs["config_file"]
        del kwargs["quiet"]
        return f(*args, **kwargs)

    return update_wrapper(t.cast(F, new_func), f)
