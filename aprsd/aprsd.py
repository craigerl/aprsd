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
import os
import signal
import sys
import time

import click
import click_completion

# local imports here
import aprsd
from aprsd import cli_helper
from aprsd import config as aprsd_config
from aprsd import messaging, packets, stats, threads, utils


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


@click.group(context_settings=CONTEXT_SETTINGS)
@click.version_option()
@click.pass_context
def cli(ctx):
    pass


def main():
    # First import all the possible commands for the CLI
    # The commands themselves live in the cmds directory
    from .cmds import (  # noqa
        completion, dev, healthcheck, list_plugins, listen, send_message,
        server,
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
    """This dumps the config to stdout."""
    click.echo(aprsd_config.dump_default_cfg())


@cli.command()
@click.pass_context
def version(ctx):
    """Show the APRSD version."""
    click.echo(click.style("APRSD Version : ", fg="white"), nl=False)
    click.secho(f"{aprsd.__version__}", fg="yellow", bold=True)


if __name__ == "__main__":
    main()
