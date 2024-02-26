import logging
import signal
import sys

import click
from oslo_config import cfg

import aprsd
from aprsd import cli_helper, client
from aprsd import main as aprsd_main
from aprsd import packets, plugin, threads, utils
from aprsd.main import cli
from aprsd.rpc import server as rpc_server
from aprsd.threads import registry, rx, tx


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
    signal.signal(signal.SIGINT, aprsd_main.signal_handler)
    signal.signal(signal.SIGTERM, aprsd_main.signal_handler)

    level, msg = utils._check_version()
    if level:
        LOG.warning(msg)
    else:
        LOG.info(msg)
    LOG.info(f"APRSD Started version: {aprsd.__version__}")

    # Initialize the client factory and create
    # The correct client object ready for use
    client.ClientFactory.setup()

    # Create the initial PM singleton and Register plugins
    # We register plugins first here so we can register each
    # plugins config options, so we can dump them all in the
    # log file output.
    LOG.info("Loading Plugin Manager and registering plugins")
    plugin_manager = plugin.PluginManager()
    plugin_manager.setup_plugins()

    # Dump all the config options now.
    CONF.log_opt_values(LOG, logging.DEBUG)
    message_plugins = plugin_manager.get_message_plugins()
    watchlist_plugins = plugin_manager.get_watchlist_plugins()
    LOG.info("Message Plugins enabled and running:")
    for p in message_plugins:
        LOG.info(p)
    LOG.info("Watchlist Plugins enabled and running:")
    for p in watchlist_plugins:
        LOG.info(p)

    # Make sure we have 1 client transport enabled
    if not client.factory.is_client_enabled():
        LOG.error("No Clients are enabled in config.")
        sys.exit(-1)

    if not client.factory.is_client_configured():
        LOG.error("APRS client is not properly configured in config file.")
        sys.exit(-1)

    # Creates the client object
    # LOG.info("Creating client connection")
    # client.factory.create().client

    # Now load the msgTrack from disk if any
    packets.PacketList()
    if flush:
        LOG.debug("Deleting saved MsgTrack.")
        packets.PacketTrack().flush()
        packets.WatchList().flush()
        packets.SeenList().flush()
    else:
        # Try and load saved MsgTrack list
        LOG.debug("Loading saved MsgTrack object.")
        packets.PacketTrack().load()
        packets.WatchList().load()
        packets.SeenList().load()

    keepalive = threads.KeepAliveThread()
    keepalive.start()

    rx_thread = rx.APRSDPluginRXThread(
        packet_queue=threads.packet_queue,
    )
    process_thread = rx.APRSDPluginProcessPacketThread(
        packet_queue=threads.packet_queue,
    )
    rx_thread.start()
    process_thread.start()

    packets.PacketTrack().restart()
    if CONF.enable_beacon:
        LOG.info("Beacon Enabled.  Starting Beacon thread.")
        bcn_thread = tx.BeaconSendThread()
        bcn_thread.start()

    if CONF.aprs_registry.enabled:
        LOG.info("Registry Enabled.  Starting Registry thread.")
        registry_thread = registry.APRSRegistryThread()
        registry_thread.start()

    if CONF.rpc_settings.enabled:
        rpc = rpc_server.APRSDRPCThread()
        rpc.start()
        log_monitor = threads.log_monitor.LogMonitorThread()
        log_monitor.start()

    rx_thread.join()
    process_thread.join()

    return 0
