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
import logging
import sys
import time
from importlib.metadata import version as metadata_version

import click
from oslo_config import cfg, generator

# local imports here
import aprsd
from aprsd import cli_helper, packets, threads, utils
from aprsd.stats import collector

# setup the global logger
# log.basicConfig(level=log.DEBUG) # level=10
CONF = cfg.CONF
LOG = logging.getLogger('APRSD')
CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


@click.group(cls=cli_helper.AliasedGroup, context_settings=CONTEXT_SETTINGS)
@click.version_option()
@click.pass_context
def cli(ctx):
    pass


def load_commands():
    from .cmds import (  # noqa
        completion,
        dev,
        fetch_stats,
        healthcheck,
        list_plugins,
        listen,
        send_message,
        server,
    )


def main():
    # First import all the possible commands for the CLI
    # The commands themselves live in the cmds directory
    load_commands()
    utils.load_entry_points('aprsd.extension')
    cli(auto_envvar_prefix='APRSD')


def signal_handler(sig, frame):
    click.echo('signal_handler: called')
    threads.APRSDThreadList().stop_all()
    if 'subprocess' not in str(frame):
        LOG.info(
            'Ctrl+C, Sending all threads exit! Can take up to 10 seconds {}'.format(
                datetime.datetime.now(),
            ),
        )
        time.sleep(1.5)
        try:
            packets.PacketTrack().save()
            packets.WatchList().save()
            packets.SeenList().save()
            packets.PacketList().save()
            collector.Collector().collect()
        except Exception as e:
            LOG.error(f'Failed to save data: {e}')
            sys.exit(0)
        # signal.signal(signal.SIGTERM, sys.exit(0))
        # sys.exit(0)


@cli.command()
@cli_helper.add_options(cli_helper.common_options)
@click.pass_context
@cli_helper.process_standard_options_no_config
def check_version(ctx):
    """Check this version against the latest in pypi.org."""
    level, msg = utils._check_version()
    if level:
        click.secho(msg, fg='yellow')
    else:
        click.secho(msg, fg='green')


@cli.command()
@click.pass_context
def sample_config(ctx):
    """Generate a sample Config file from aprsd and all installed plugins."""

    def _get_selected_entry_points():
        import sys

        if sys.version_info < (3, 10):
            all = imp.entry_points()
            selected = []
            if 'oslo.config.opts' in all:
                for x in all['oslo.config.opts']:
                    if x.group == 'oslo.config.opts':
                        selected.append(x)
        else:
            selected = imp.entry_points(group='oslo.config.opts')

        return selected

    def get_namespaces():
        args = []

        # selected = imp.entry_points(group="oslo.config.opts")
        selected = _get_selected_entry_points()
        for entry in selected:
            if 'aprsd' in entry.name:
                args.append('--namespace')
                args.append(entry.name)

        return args

    args = get_namespaces()
    config_version = metadata_version('oslo.config')
    logging.basicConfig(level=logging.WARN)
    conf = cfg.ConfigOpts()
    generator.register_cli_opts(conf)
    try:
        conf(args, version=config_version)
    except cfg.RequiredOptError as ex:
        conf.print_help()
        if not sys.argv[1:]:
            raise SystemExit from ex
        raise
    generator.generate(conf)
    return


@cli.command()
@click.pass_context
def version(ctx):
    """Show the APRSD version."""
    click.echo(click.style('APRSD Version : ', fg='white'), nl=False)
    click.secho(f'{aprsd.__version__}', fg='yellow', bold=True)


if __name__ == '__main__':
    main()
