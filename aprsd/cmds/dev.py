#
#  Dev.py is used to help develop plugins
#
#
# python included libs
import logging

import click

# local imports here
from aprsd import cli_helper, client, messaging, packets, plugin, stats

from ..aprsd import cli


LOG = logging.getLogger("APRSD")
CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@cli.group(help="Development type subcommands", context_settings=CONTEXT_SETTINGS)
@click.pass_context
def dev(ctx):
    pass


@dev.command()
@cli_helper.add_options(cli_helper.common_options)
@click.option(
    "--aprs-login",
    envvar="APRS_LOGIN",
    show_envvar=True,
    help="What callsign to send the message from.",
)
@click.option(
    "-p",
    "--plugin",
    "plugin_path",
    show_default=True,
    default=None,
    help="The plugin to run.  Ex: aprsd.plugins.ping.PingPlugin",
)
@click.option(
    "-a",
    "--all",
    "load_all",
    show_default=True,
    is_flag=True,
    default=False,
    help="Load all the plugins in config?",
)
@click.option(
    "-n",
    "--num",
    "number",
    show_default=True,
    default=1,
    help="Number of times to call the plugin",
)
@click.argument("message", nargs=-1, required=True)
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
    config = ctx.obj["config"]
    fromcall = aprs_login

    if not plugin_path:
        click.echo(ctx.get_help())
        click.echo("")
        ctx.fail("Failed to provide -p option to test a plugin")
        ctx.exit()

    if type(message) is tuple:
        message = " ".join(message)
    client.Client(config)
    stats.APRSDStats(config)
    messaging.MsgTrack(config=config)
    packets.WatchList(config=config)
    packets.SeenList(config=config)

    pm = plugin.PluginManager(config)
    if load_all:
        pm.setup_plugins()
    else:
        pm._init()
    obj = pm._create_class(plugin_path, plugin.APRSDPluginBase, config=config)
    if not obj:
        click.echo(ctx.get_help())
        click.echo("")
        ctx.fail(f"Failed to create object from plugin path '{plugin_path}'")
        ctx.exit()

    # Register the plugin they wanted tested.
    LOG.info(
        "Testing plugin {} Version {}".format(
            obj.__class__, obj.version,
        ),
    )
    pm._pluggy_pm.register(obj)
    login = config["aprs"]["login"]

    packet = {
        "from": fromcall, "addresse": login,
        "message_text": message,
        "format": "message",
        "msgNo": 1,
    }
    LOG.info(f"P'{plugin_path}'  F'{fromcall}'   C'{message}'")

    for x in range(number):
        reply = pm.run(packet)
        # Plugin might have threads, so lets stop them so we can exit.
        # obj.stop_threads()
        LOG.info(f"Result{x} = '{reply}'")
    pm.stop()
