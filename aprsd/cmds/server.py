import logging
import signal
import sys

import click
from oslo_config import cfg

import aprsd
from aprsd import aprsd as aprsd_main
from aprsd import cli_helper, client, flask, packets, plugin, threads, utils
from aprsd.aprsd import cli
from aprsd.threads import rx


CONF = cfg.CONF
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
    loglevel = ctx.obj["loglevel"]
    quiet = ctx.obj["quiet"]

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

    CONF.log_opt_values(LOG, logging.DEBUG)

    # Initialize the client factory and create
    # The correct client object ready for use
    client.ClientFactory.setup()
    # Make sure we have 1 client transport enabled
    if not client.factory.is_client_enabled():
        LOG.error("No Clients are enabled in config.")
        sys.exit(-1)

    if not client.factory.is_client_configured():
        LOG.error("APRS client is not properly configured in config file.")
        sys.exit(-1)

    # Creates the client object
    LOG.info("Creating client connection")
    client.factory.create().client

    # Now load the msgTrack from disk if any
    packets.PacketList()
    if flush:
        LOG.debug("Deleting saved MsgTrack.")
        packets.PacketTrack().flush()
        packets.WatchList()
        packets.SeenList()
    else:
        # Try and load saved MsgTrack list
        LOG.debug("Loading saved MsgTrack object.")
        packets.PacketTrack().load()
        packets.WatchList().load()
        packets.SeenList().load()

    # Create the initial PM singleton and Register plugins
    LOG.info("Loading Plugin Manager and registering plugins")
    plugin_manager = plugin.PluginManager()
    plugin_manager.setup_plugins()

    rx_thread = rx.APRSDPluginRXThread(
        packet_queue=threads.packet_queue,
    )
    process_thread = rx.APRSDPluginProcessPacketThread(
        packet_queue=threads.packet_queue,
    )
    rx_thread.start()
    process_thread.start()

    packets.PacketTrack().restart()

    keepalive = threads.KeepAliveThread()
    keepalive.start()

    web_enabled = CONF.admin.web_enabled

    if web_enabled:
        aprsd_main.flask_enabled = True
        (socketio, app) = flask.init_flask(loglevel, quiet)
        socketio.run(
            app,
            allow_unsafe_werkzeug=True,
            host=CONF.admin.web_ip,
            port=CONF.admin.web_port,
        )

    # If there are items in the msgTracker, then save them
    LOG.info("APRSD Exiting.")
    return 0
