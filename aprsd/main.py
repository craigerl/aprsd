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
import importlib.metadata as imp
from importlib.metadata import version as metadata_version
import logging
import os
import signal
import sys
import time

import click
import click_completion
from oslo_config import cfg, generator

# local imports here
import aprsd
from aprsd import cli_helper, packets, stats, threads, utils


# setup the global logger
# log.basicConfig(level=log.DEBUG) # level=10
CONF = cfg.CONF
LOG = logging.getLogger("APRSD")
CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])
flask_enabled = False
rpc_serv = None


def custom_startswith(string, incomplete):
    """A custom completion match that supports case insensitive matching."""
    if os.environ.get("_CLICK_COMPLETION_COMMAND_CASE_INSENSITIVE_COMPLETE"):
        string = string.lower()
        incomplete = incomplete.lower()
    return string.startswith(incomplete)


click_completion.core.startswith = custom_startswith
click_completion.init()


@click.group(cls=cli_helper.AliasedGroup, context_settings=CONTEXT_SETTINGS)
@click.version_option()
@click.pass_context
def cli(ctx):
    pass


def load_commands():
    from .cmds import (  # noqa
        completion, dev, fetch_stats, healthcheck, list_plugins, listen,
        send_message, server, webchat,
    )


def main():
    # First import all the possible commands for the CLI
    # The commands themselves live in the cmds directory
    load_commands()
    utils.load_entry_points("aprsd.extension")
    cli(auto_envvar_prefix="APRSD")


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
        packets.PacketTrack().save()
        packets.WatchList().save()
        packets.SeenList().save()
        LOG.info(stats.APRSDStats())
        # signal.signal(signal.SIGTERM, sys.exit(0))
        # sys.exit(0)

    if flask_enabled:
        signal.signal(signal.SIGTERM, sys.exit(0))


@cli.command()
@cli_helper.add_options(cli_helper.common_options)
@click.pass_context
@cli_helper.process_standard_options_no_config
def check_version(ctx):
    """Check this version against the latest in pypi.org."""
    level, msg = utils._check_version()
    if level:
        click.secho(msg, fg="yellow")
    else:
        click.secho(msg, fg="green")


@cli.command()
@click.pass_context
def sample_config(ctx):
    """Generate a sample Config file from aprsd and all installed plugins."""

    def get_namespaces():
        args = []

        selected = imp.entry_points(group="oslo.config.opts")
        for entry in selected:
            if "aprsd" in entry.name:
                args.append("--namespace")
                args.append(entry.name)

        return args

    args = get_namespaces()
    config_version = metadata_version("oslo.config")
    logging.basicConfig(level=logging.WARN)
    conf = cfg.ConfigOpts()
    generator.register_cli_opts(conf)
    try:
        conf(args, version=config_version)
    except cfg.RequiredOptError:
        conf.print_help()
        if not sys.argv[1:]:
            raise SystemExit
        raise
    LOG.warning(conf.namespace)
    generator.generate(conf)
    return


@cli.command()
@click.pass_context
def version(ctx):
    """Show the APRSD version."""
    click.echo(click.style("APRSD Version : ", fg="white"), nl=False)
    click.secho(f"{aprsd.__version__}", fg="yellow", bold=True)


if __name__ == "__main__":
    main()
