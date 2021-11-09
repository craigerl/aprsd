import logging
import signal
import sys

import click

import aprsd
from aprsd import (
    cli_helper, client, flask, messaging, packets, plugin, stats, threads,
    trace, utils,
)
from aprsd import aprsd as aprsd_main

from ..aprsd import cli


LOG = logging.getLogger("APRSD")


# main() ###
@cli.command()
@cli_helper.add_options(cli_helper.common_options)
@click.option(
    "-f",
    "--flush",
    "flush",
    is_flag=True,
    show_default=True,
    default=False,
    help="Flush out all old aged messages on disk.",
)
@click.pass_context
@cli_helper.process_standard_options
def server(ctx, flush):
    """Start the aprsd server gateway process."""
    ctx.obj["config_file"]
    loglevel = ctx.obj["loglevel"]
    quiet = ctx.obj["quiet"]
    config = ctx.obj["config"]

    signal.signal(signal.SIGINT, aprsd_main.signal_handler)
    signal.signal(signal.SIGTERM, aprsd_main.signal_handler)

    if not quiet:
        click.echo("Load config")

    level, msg = utils._check_version()
    if level:
        LOG.warning(msg)
    else:
        LOG.info(msg)
    LOG.info(f"APRSD Started version: {aprsd.__version__}")

    flat_config = utils.flatten_dict(config)
    LOG.info("Using CONFIG values:")
    for x in flat_config:
        if "password" in x or "aprsd.web.users.admin" in x:
            LOG.info(f"{x} = XXXXXXXXXXXXXXXXXXX")
        else:
            LOG.info(f"{x} = {flat_config[x]}")

    if config["aprsd"].get("trace", False):
        trace.setup_tracing(["method", "api"])
    stats.APRSDStats(config)

    # Initialize the client factory and create
    # The correct client object ready for use
    client.ClientFactory.setup(config)
    # Make sure we have 1 client transport enabled
    if not client.factory.is_client_enabled():
        LOG.error("No Clients are enabled in config.")
        sys.exit(-1)

    # Creates the client object
    LOG.info("Creating client connection")
    client.factory.create().client

    # Now load the msgTrack from disk if any
    packets.PacketList(config=config)
    if flush:
        LOG.debug("Deleting saved MsgTrack.")
        messaging.MsgTrack(config=config).flush()
        packets.WatchList(config=config)
        packets.SeenList(config=config)
    else:
        # Try and load saved MsgTrack list
        LOG.debug("Loading saved MsgTrack object.")
        messaging.MsgTrack(config=config).load()
        packets.WatchList(config=config).load()
        packets.SeenList(config=config).load()

    # Create the initial PM singleton and Register plugins
    LOG.info("Loading Plugin Manager and registering plugins")
    plugin_manager = plugin.PluginManager(config)
    plugin_manager.setup_plugins()

    rx_thread = threads.APRSDRXThread(
        msg_queues=threads.msg_queues,
        config=config,
    )
    rx_thread.start()

    messaging.MsgTrack().restart()

    keepalive = threads.KeepAliveThread(config=config)
    keepalive.start()

    web_enabled = config.get("aprsd.web.enabled", default=False)

    if web_enabled:
        aprsd_main.flask_enabled = True
        (socketio, app) = flask.init_flask(config, loglevel, quiet)
        socketio.run(
            app,
            host=config["aprsd"]["web"]["host"],
            port=config["aprsd"]["web"]["port"],
        )

    # If there are items in the msgTracker, then save them
    LOG.info("APRSD Exiting.")
    return 0
