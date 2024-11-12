import logging
import signal
import sys

import click
from oslo_config import cfg

import aprsd
from aprsd import cli_helper
from aprsd import main as aprsd_main
from aprsd import plugin, threads, utils
from aprsd.client import client_factory
from aprsd.main import cli
from aprsd.packets import collector as packet_collector
from aprsd.packets import seen_list
from aprsd.threads import keep_alive, log_monitor, registry, rx
from aprsd.threads import stats as stats_thread
from aprsd.threads import tx


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
    if not client_factory.is_client_enabled():
        LOG.error("No Clients are enabled in config.")
        sys.exit(-1)

    # Creates the client object
    LOG.info("Creating client connection")
    aprs_client = client_factory.create()
    LOG.info(aprs_client)

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
    if not client_factory.is_client_enabled():
        LOG.error("No Clients are enabled in config.")
        sys.exit(-1)

    if not client_factory.is_client_configured():
        LOG.error("APRS client is not properly configured in config file.")
        sys.exit(-1)

    if not CONF.enable_seen_list:
        # just deregister the class from the packet collector
        packet_collector.PacketCollector().unregister(seen_list.SeenList)

    # Now load the msgTrack from disk if any
    if flush:
        LOG.debug("Flushing All packet tracking objects.")
        packet_collector.PacketCollector().flush()
    else:
        # Try and load saved MsgTrack list
        LOG.debug("Loading saved packet tracking data.")
        packet_collector.PacketCollector().load()

    # Now start all the main processing threads.

    keepalive = keep_alive.KeepAliveThread()
    keepalive.start()

    stats_store_thread = stats_thread.APRSDStatsStoreThread()
    stats_store_thread.start()

    rx_thread = rx.APRSDPluginRXThread(
        packet_queue=threads.packet_queue,
    )
    process_thread = rx.APRSDPluginProcessPacketThread(
        packet_queue=threads.packet_queue,
    )
    rx_thread.start()
    process_thread.start()

    if CONF.enable_beacon:
        LOG.info("Beacon Enabled.  Starting Beacon thread.")
        bcn_thread = tx.BeaconSendThread()
        bcn_thread.start()

    if CONF.aprs_registry.enabled:
        LOG.info("Registry Enabled.  Starting Registry thread.")
        registry_thread = registry.APRSRegistryThread()
        registry_thread.start()

    if CONF.admin.web_enabled:
        log_monitor_thread = log_monitor.LogMonitorThread()
        log_monitor_thread.start()

    rx_thread.join()
    process_thread.join()

    return 0
