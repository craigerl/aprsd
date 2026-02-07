#
#  Dev.py is used to help develop plugins
#
#
# python included libs
import logging
import sys

import click
from oslo_config import cfg

import aprsd
import aprsd.packets.log as packet_log
from aprsd import cli_helper, packets, plugin, utils

# local imports here
from aprsd.main import cli
from aprsd.utils import trace

CONF = cfg.CONF
LOG = logging.getLogger('APRSD')
CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


@cli.group(help='Development type subcommands', context_settings=CONTEXT_SETTINGS)
@click.pass_context
def dev(ctx):
    pass


@dev.command()
@cli_helper.add_options(cli_helper.common_options)
@click.option(
    '--aprs-login',
    envvar='APRS_LOGIN',
    show_envvar=True,
    help='What callsign to send the message from.',
)
@click.option(
    '-p',
    '--plugin',
    'plugin_path',
    show_default=True,
    default=None,
    help='The plugin to run.  Ex: aprsd.plugins.ping.PingPlugin',
)
@click.option(
    '-a',
    '--all',
    'load_all',
    show_default=True,
    is_flag=True,
    default=False,
    help='Load all the plugins in config?',
)
@click.option(
    '-n',
    '--num',
    'number',
    show_default=True,
    default=1,
    help='Number of times to call the plugin',
)
@click.argument('message', nargs=-1, required=True)
@click.pass_context
@cli_helper.process_standard_options
def test_plugin(
    ctx,
    aprs_login,
    plugin_path,
    load_all,
    number,
    message,
):
    """Test an individual APRSD plugin given a python path."""

    LOG.info(f'Python version: {sys.version}')
    LOG.info(f'APRSD DEV Started version: {aprsd.__version__}')
    utils.package.log_installed_extensions_and_plugins()
    CONF.log_opt_values(LOG, logging.DEBUG)

    if not aprs_login:
        if CONF.callsign == 'NOCALL':
            click.echo(
                'Must set --aprs_login or APRS_LOGIN, or set callsign in config ([DEFAULT])'
            )
            ctx.exit(-1)
            return
        fromcall = CONF.callsign
    else:
        fromcall = aprs_login

    if not plugin_path:
        click.echo(ctx.get_help())
        click.echo('')
        click.echo('Failed to provide -p option to test a plugin')
        ctx.exit(-1)
        return

    if type(message) is tuple:
        message = ' '.join(message)

    if CONF.trace_enabled:
        trace.setup_tracing(['method', 'api'])

    pm = plugin.PluginManager()
    if load_all:
        pm.setup_plugins(load_help_plugin=CONF.load_help_plugin)
    obj = pm._create_class(plugin_path, plugin.APRSDPluginBase)
    if not obj:
        click.echo(ctx.get_help())
        click.echo('')
        ctx.fail(f"Failed to create object from plugin path '{plugin_path}'")
        ctx.exit()

    # Register the plugin they wanted tested.
    LOG.info(
        'Testing plugin {} Version {}'.format(
            obj.__class__,
            obj.version,
        ),
    )
    pm.register_msg(obj)

    packet = packets.MessagePacket(
        from_call=fromcall,
        to_call=CONF.callsign,
        msgNo=1,
        message_text=message,
    )
    LOG.info(f"P'{plugin_path}'  F'{fromcall}'   C'{message}'")
    packet_log.log(packet)

    for _ in range(number):
        # PluginManager.run() executes all plugins in parallel
        # Results may be in a different order than plugin registration
        # NULL_MESSAGE results are already filtered out
        results, handled = pm.run(packet)
        LOG.debug(f'Replies: {results}')
        # Plugin might have threads, so lets stop them so we can exit.
        # obj.stop_threads()
        for reply in results:
            if isinstance(reply, list):
                # one of the plugins wants to send multiple messages
                for subreply in reply:
                    if isinstance(subreply, packets.Packet):
                        LOG.info(subreply)
                    else:
                        LOG.info(
                            packets.MessagePacket(
                                from_call=CONF.callsign,
                                to_call=fromcall,
                                message_text=subreply,
                            ),
                        )
            elif isinstance(reply, packets.Packet):
                # We have a message based object.
                LOG.info(reply)
            else:
                # Note: NULL_MESSAGE results are already filtered out
                # in PluginManager.run(), but keeping this check for safety
                if reply is not packets.NULL_MESSAGE:
                    LOG.debug(f'Reply: {reply}')
                    LOG.info(
                        packets.MessagePacket(
                            from_call=CONF.callsign,
                            to_call=fromcall,
                            message_text=reply,
                        ),
                    )
    pm.stop()
