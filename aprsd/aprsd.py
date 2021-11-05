#
# Listen on amateur radio aprs-is network for messages and respond to them.
# You must have an amateur radio callsign to use this software.  You must
# create an ~/.aprsd/config.yml file with all of the required settings.  To
# generate an example config.yml, just run aprsd, then copy the sample config
# to ~/.aprsd/config.yml and edit the settings.
#
# APRS messages:
#   l(ocation)             = descriptive location of calling station
#   w(eather)              = temp, (hi/low) forecast, later forecast
#   t(ime)                 = respond with the current time
#   f(ortune)              = respond with a short fortune
#   -email_addr email text = send an email
#   -2                     = display the last 2 emails received
#   p(ing)                 = respond with Pong!/time
#   anything else          = respond with usage
#
# (C)2018 Craig Lamparter
# License GPLv2
#

# python included libs
import datetime
import logging
from logging import NullHandler
from logging.handlers import RotatingFileHandler
import os
import signal
import sys
import time

import click
import click_completion

# local imports here
import aprsd
from aprsd import config as aprsd_config
from aprsd import messaging, packets, stats, threads, utils
from aprsd.cli_helper import AliasedGroup


# setup the global logger
# logging.basicConfig(level=logging.DEBUG) # level=10
LOG = logging.getLogger("APRSD")
CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])
flask_enabled = False


def custom_startswith(string, incomplete):
    """A custom completion match that supports case insensitive matching."""
    if os.environ.get("_CLICK_COMPLETION_COMMAND_CASE_INSENSITIVE_COMPLETE"):
        string = string.lower()
        incomplete = incomplete.lower()
    return string.startswith(incomplete)


click_completion.core.startswith = custom_startswith
click_completion.init()


@click.group(cls=AliasedGroup, context_settings=CONTEXT_SETTINGS)
@click.option(
    "--loglevel",
    default="INFO",
    show_default=True,
    type=click.Choice(
        ["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
        case_sensitive=False,
    ),
    show_choices=True,
    help="The log level to use for aprsd.log",
)
@click.option(
    "-c",
    "--config",
    "config_file",
    show_default=True,
    default=aprsd_config.DEFAULT_CONFIG_FILE,
    help="The aprsd config file to use for options.",
)
@click.option(
    "--quiet",
    is_flag=True,
    default=False,
    help="Don't log to stdout",
)
@click.version_option()
@click.pass_context
def cli(ctx, loglevel, config_file, quiet):
    ctx.ensure_object(dict)
    ctx.obj["loglevel"] = loglevel
    ctx.obj["config_file"] = config_file
    ctx.obj["quiet"] = quiet
    ctx.obj["config"] = aprsd_config.parse_config(config_file)
    setup_logging(ctx.obj["config"], loglevel, quiet)


def main():
    from .cmds import (  # noqa
        completion, dev, healthcheck, listen, send_message, server,
    )
    cli()


def signal_handler(sig, frame):
    global flask_enabled

    click.echo("signal_handler: called")
    threads.APRSDThreadList().stop_all()
    if "subprocess" not in str(frame):
        LOG.info(
            "Ctrl+C, Sending all threads exit! Can take up to 10 seconds {}".format(
                datetime.datetime.now(),
            ),
        )
        time.sleep(1.5)
        messaging.MsgTrack().save()
        packets.WatchList().save()
        packets.SeenList().save()
        LOG.info(stats.APRSDStats())
        # signal.signal(signal.SIGTERM, sys.exit(0))
        # sys.exit(0)
    if flask_enabled:
        signal.signal(signal.SIGTERM, sys.exit(0))


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
        qh = logging.handlers.QueueHandler(threads.logging_queue)
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


@cli.command()
@click.pass_context
def check_version(ctx):
    """Check this version against the latest in pypi.org."""
    config_file = ctx.obj["config_file"]
    loglevel = ctx.obj["loglevel"]
    config = aprsd_config.parse_config(config_file)

    setup_logging(config, loglevel, False)
    level, msg = utils._check_version()
    if level:
        LOG.warning(msg)
    else:
        LOG.info(msg)


@cli.command()
@click.pass_context
def sample_config(ctx):
    """This dumps the config to stdout."""
    click.echo(aprsd_config.dump_default_cfg())


@cli.command()
@click.pass_context
def version(ctx):
    """Show the APRSD version."""
    click.echo(f"APRSD Version : {aprsd.__version__}")


if __name__ == "__main__":
    main()
