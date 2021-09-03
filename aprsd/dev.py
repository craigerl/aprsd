#
#  Dev.py is used to help develop plugins
#
#
# python included libs
import logging
from logging import NullHandler
from logging.handlers import RotatingFileHandler
import os
import sys

import click
import click_completion

# local imports here
import aprsd
from aprsd import client, plugin, utils


# setup the global logger
# logging.basicConfig(level=logging.DEBUG) # level=10
LOG = logging.getLogger("APRSD")

LOG_LEVELS = {
    "CRITICAL": logging.CRITICAL,
    "ERROR": logging.ERROR,
    "WARNING": logging.WARNING,
    "INFO": logging.INFO,
    "DEBUG": logging.DEBUG,
}

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


def custom_startswith(string, incomplete):
    """A custom completion match that supports case insensitive matching."""
    if os.environ.get("_CLICK_COMPLETION_COMMAND_CASE_INSENSITIVE_COMPLETE"):
        string = string.lower()
        incomplete = incomplete.lower()
    return string.startswith(incomplete)


click_completion.core.startswith = custom_startswith
click_completion.init()


cmd_help = """Shell completion for click-completion-command
Available shell types:
\b
  %s
Default type: auto
""" % "\n  ".join(
    f"{k:<12} {click_completion.core.shells[k]}"
    for k in sorted(click_completion.core.shells.keys())
)


@click.group(help=cmd_help, context_settings=CONTEXT_SETTINGS)
@click.version_option()
def main():
    pass


@main.command()
@click.option(
    "-i",
    "--case-insensitive/--no-case-insensitive",
    help="Case insensitive completion",
)
@click.argument(
    "shell",
    required=False,
    type=click_completion.DocumentedChoice(click_completion.core.shells),
)
def show(shell, case_insensitive):
    """Show the click-completion-command completion code"""
    extra_env = (
        {"_CLICK_COMPLETION_COMMAND_CASE_INSENSITIVE_COMPLETE": "ON"}
        if case_insensitive
        else {}
    )
    click.echo(click_completion.core.get_code(shell, extra_env=extra_env))


@main.command()
@click.option(
    "--append/--overwrite",
    help="Append the completion code to the file",
    default=None,
)
@click.option(
    "-i",
    "--case-insensitive/--no-case-insensitive",
    help="Case insensitive completion",
)
@click.argument(
    "shell",
    required=False,
    type=click_completion.DocumentedChoice(click_completion.core.shells),
)
@click.argument("path", required=False)
def install(append, case_insensitive, shell, path):
    """Install the click-completion-command completion"""
    extra_env = (
        {"_CLICK_COMPLETION_COMMAND_CASE_INSENSITIVE_COMPLETE": "ON"}
        if case_insensitive
        else {}
    )
    shell, path = click_completion.core.install(
        shell=shell,
        path=path,
        append=append,
        extra_env=extra_env,
    )
    click.echo(f"{shell} completion installed in {path}")


# Setup the logging faciility
# to disable logging to stdout, but still log to file
# use the --quiet option on the cmdln
def setup_logging(config, loglevel, quiet):
    log_level = LOG_LEVELS[loglevel]
    LOG.setLevel(log_level)
    log_format = "[%(asctime)s] [%(threadName)-12s] [%(levelname)-5.5s]" " %(message)s"
    date_format = "%m/%d/%Y %I:%M:%S %p"
    log_formatter = logging.Formatter(fmt=log_format, datefmt=date_format)
    log_file = config["aprs"].get("logfile", None)
    if log_file:
        fh = RotatingFileHandler(log_file, maxBytes=(10248576 * 5), backupCount=4)
    else:
        fh = NullHandler()

    fh.setFormatter(log_formatter)
    LOG.addHandler(fh)

    if not quiet:
        sh = logging.StreamHandler(sys.stdout)
        sh.setFormatter(log_formatter)
        LOG.addHandler(sh)


@main.command()
@click.option(
    "--loglevel",
    default="DEBUG",
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
    default=utils.DEFAULT_CONFIG_FILE,
    help="The aprsd config file to use for options.",
)
@click.option(
    "-p",
    "--plugin",
    "plugin_path",
    show_default=True,
    default="aprsd.plugins.wx.WxPlugin",
    help="The plugin to run",
)
@click.argument("fromcall")
@click.argument("message", nargs=-1, required=True)
def test_plugin(
    loglevel,
    config_file,
    plugin_path,
    fromcall,
    message,
):
    """APRSD Plugin test app."""

    config = utils.parse_config(config_file)

    setup_logging(config, loglevel, False)
    LOG.info(f"Test APRSD PLugin version: {aprsd.__version__}")
    if type(message) is tuple:
        message = " ".join(message)
    LOG.info(f"P'{plugin_path}'  F'{fromcall}'   C'{message}'")
    client.Client(config)

    pm = plugin.PluginManager(config)
    obj = pm._create_class(plugin_path, plugin.APRSDPluginBase, config=config)
    login = config["aprs"]["login"]

    packet = {
        "from": fromcall, "addresse": login,
        "message_text": message,
        "format": "message",
        "msgNo": 1,
    }

    reply = obj.filter(packet)
    # Plugin might have threads, so lets stop them so we can exit.
    obj.stop_threads()
    LOG.info(f"Result = '{reply}'")


if __name__ == "__main__":
    main()
