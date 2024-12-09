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
from aprsd.threads import aprsd as aprsd_threads
from aprsd.threads import keep_alive, registry, rx
from aprsd.threads import stats as stats_thread
from aprsd.threads import tx
from aprsd.utils import singleton


CONF = cfg.CONF
LOG = logging.getLogger("APRSD")


@singleton
class ServerThreads:
    """Registry for threads that the server command runs.

    This enables extensions to register a thread to run during
    the server command.

    """
    def __init__(self):
        self.threads: list[aprsd_threads.APRSDThread] = []

    def register(self, thread: aprsd_threads.APRSDThread):
        if not isinstance(thread, aprsd_threads.APRSDThread):
            raise TypeError(f"Thread {thread} is not an APRSDThread")
        self.threads.append(thread)

    def unregister(self, thread: aprsd_threads.APRSDThread):
        if not isinstance(thread, aprsd_threads.APRSDThread):
            raise TypeError(f"Thread {thread} is not an APRSDThread")
        self.threads.remove(thread)

    def start(self):
        """Start all threads in the list."""
        for thread in self.threads:
            thread.start()

    def join(self):
        """Join all the threads in the list"""
        for thread in self.threads:
            thread.join()


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

    server_threads = ServerThreads()

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

    # Make sure we have 1 client transport enabled
    if not client_factory.is_client_enabled():
        LOG.error("No Clients are enabled in config.")
        sys.exit(-1)

    if not client_factory.is_client_configured():
        LOG.error("APRS client is not properly configured in config file.")
        sys.exit(-1)

    # Creates the client object
    LOG.info("Creating client connection")
    aprs_client = client_factory.create()
    LOG.info(aprs_client)
    if not aprs_client.login_success:
        # We failed to login, will just quit!
        msg = f"Login Failure: {aprs_client.login_failure}"
        LOG.error(msg)
        print(msg)
        sys.exit(-1)

    # Check to make sure the login worked.

    # Create the initial PM singleton and Register plugins
    # We register plugins first here so we can register each
    # plugins config options, so we can dump them all in the
    # log file output.
    LOG.info("Loading Plugin Manager and registering plugins")
    plugin_manager = plugin.PluginManager()
    plugin_manager.setup_plugins(load_help_plugin=CONF.load_help_plugin)

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

    server_threads.register(keep_alive.KeepAliveThread())
    server_threads.register(stats_thread.APRSDStatsStoreThread())
    server_threads.register(
        rx.APRSDPluginRXThread(
            packet_queue=threads.packet_queue,
        ),
    )
    server_threads.register(
        rx.APRSDPluginProcessPacketThread(
            packet_queue=threads.packet_queue,
        ),
    )

    if CONF.enable_beacon:
        LOG.info("Beacon Enabled.  Starting Beacon thread.")
        server_threads.register(tx.BeaconSendThread())

    if CONF.aprs_registry.enabled:
        LOG.info("Registry Enabled.  Starting Registry thread.")
        server_threads.register(registry.APRSRegistryThread())

    server_threads.start()
    server_threads.join()

    return 0
