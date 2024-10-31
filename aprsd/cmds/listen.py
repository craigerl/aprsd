#
# License GPLv2
#

# python included libs
import datetime
import logging
import signal
import sys
import time

import click
from loguru import logger
from oslo_config import cfg
from rich.console import Console

# local imports here
import aprsd
from aprsd import cli_helper, packets, plugin, threads, utils
from aprsd.client import client_factory
from aprsd.main import cli
from aprsd.packets import collector as packet_collector
from aprsd.packets import log as packet_log
from aprsd.packets import seen_list
from aprsd.stats import collector
from aprsd.threads import keep_alive, rx
from aprsd.threads import stats as stats_thread
from aprsd.threads.aprsd import APRSDThread


# setup the global logger
# log.basicConfig(level=log.DEBUG) # level=10
LOG = logging.getLogger("APRSD")
CONF = cfg.CONF
LOGU = logger
console = Console()


def signal_handler(sig, frame):
    threads.APRSDThreadList().stop_all()
    if "subprocess" not in str(frame):
        LOG.info(
            "Ctrl+C, Sending all threads exit! Can take up to 10 seconds {}".format(
                datetime.datetime.now(),
            ),
        )
        time.sleep(5)
        # Last save to disk
        collector.Collector().collect()


@utils.singleton
class SimplePacketStats:
    def __init__(self):
        self.total_rx = 0
        self.total_tx = 0
        self.types = {}

    def rx(self, packet):
        self.total_rx += 1
        ptype = packet.__class__.__name__
        if ptype not in self.types:
            self.types[ptype] = {"tx": 0, "rx": 0}
        self.types[ptype]["rx"] += 1

    def tx(self, packet):
        self.total_tx += 1
        ptype = packet.__class__.__name__
        if ptype not in self.types:
            self.types[ptype] = {"tx": 0, "rx": 0}
        self.types[ptype]["tx"] += 1

    def flush(self):
        pass

    def load(self):
        pass

    def stats(self, serializable=False):
        return {
            "total_rx": self.total_rx,
            "total_tx": self.total_tx,
            "types": self.types,
        }


class APRSDListenThread(rx.APRSDRXThread):
    def __init__(self, packet_queue, packet_filter=None, plugin_manager=None):
        super().__init__(packet_queue)
        self.packet_filter = packet_filter
        self.plugin_manager = plugin_manager
        if self.plugin_manager:
            LOG.info(f"Plugins {self.plugin_manager.get_message_plugins()}")

    def process_packet(self, *args, **kwargs):
        packet = self._client.decode_packet(*args, **kwargs)
        filters = {
            packets.Packet.__name__: packets.Packet,
            packets.AckPacket.__name__: packets.AckPacket,
            packets.BeaconPacket.__name__: packets.BeaconPacket,
            packets.GPSPacket.__name__: packets.GPSPacket,
            packets.MessagePacket.__name__: packets.MessagePacket,
            packets.MicEPacket.__name__: packets.MicEPacket,
            packets.ObjectPacket.__name__: packets.ObjectPacket,
            packets.StatusPacket.__name__: packets.StatusPacket,
            packets.ThirdPartyPacket.__name__: packets.ThirdPartyPacket,
            packets.WeatherPacket.__name__: packets.WeatherPacket,
            packets.UnknownPacket.__name__: packets.UnknownPacket,
        }

        if self.packet_filter:
            filter_class = filters[self.packet_filter]
            if isinstance(packet, filter_class):
                packet_log.log(packet)
                if self.plugin_manager:
                    # Don't do anything with the reply
                    # This is the listen only command.
                    self.plugin_manager.run(packet)
        else:
            packet_log.log(packet)
            if self.plugin_manager:
                # Don't do anything with the reply.
                # This is the listen only command.
                self.plugin_manager.run(packet)

        packet_collector.PacketCollector().rx(packet)


class ListenStatsThread(APRSDThread):
    def __init__(self):
        super().__init__("SimpleStats")
        self._last_total_rx = 0

    def loop(self):
        if self.loop_count % 10 == 0:
            # log the stats every 10 seconds
            stats_json = collector.Collector().collect()
            stats = stats_json["PacketList"]
            total_rx = stats["rx"]
            rate = (total_rx - self._last_total_rx) / 10
            LOGU.opt(colors=True).info(
                f"<green>RX Rate: {rate} pps</green>  "
                f"<yellow>Total RX: {total_rx}</yellow> "
                f"<red>RX Last 10 secs: {total_rx - self._last_total_rx}</red>",
            )
            self._last_total_rx = total_rx
            for k, v in stats["types"].items():
                thread_hex = f"fg {utils.hex_from_name(k)}"
                LOGU.opt(colors=True).info(
                    f"<{thread_hex}>{k:<15}</{thread_hex}> "
                    f"<blue>RX: {v['rx']}</blue> <red>TX: {v['tx']}</red>",
                )

        time.sleep(1)
        return True


@cli.command()
@cli_helper.add_options(cli_helper.common_options)
@click.option(
    "--aprs-login",
    envvar="APRS_LOGIN",
    show_envvar=True,
    help="What callsign to send the message from.",
)
@click.option(
    "--aprs-password",
    envvar="APRS_PASSWORD",
    show_envvar=True,
    help="the APRS-IS password for APRS_LOGIN",
)
@click.option(
    "--packet-filter",
    type=click.Choice(
        [
            packets.AckPacket.__name__,
            packets.BeaconPacket.__name__,
            packets.GPSPacket.__name__,
            packets.MicEPacket.__name__,
            packets.MessagePacket.__name__,
            packets.ObjectPacket.__name__,
            packets.RejectPacket.__name__,
            packets.StatusPacket.__name__,
            packets.ThirdPartyPacket.__name__,
            packets.UnknownPacket.__name__,
            packets.WeatherPacket.__name__,
        ],
        case_sensitive=False,
    ),
    help="Filter by packet type",
)
@click.option(
    "--load-plugins",
    default=False,
    is_flag=True,
    help="Load plugins as enabled in aprsd.conf ?",
)
@click.argument(
    "filter",
    nargs=-1,
    required=True,
)
@click.pass_context
@cli_helper.process_standard_options
def listen(
    ctx,
    aprs_login,
    aprs_password,
    packet_filter,
    load_plugins,
    filter,
):
    """Listen to packets on the APRS-IS Network based on FILTER.

    FILTER is the APRS Filter to use.\n
     see http://www.aprs-is.net/javAPRSFilter.aspx\n
    r/lat/lon/dist - Range Filter Pass posits and objects within dist km from lat/lon.\n
    p/aa/bb/cc... - Prefix Filter Pass traffic with fromCall that start with aa or bb or cc.\n
    b/call1/call2... - Budlist Filter Pass all traffic from exact call: call1, call2, ... (* wild card allowed) \n
    o/obj1/obj2... - Object Filter Pass all objects with the exact name of obj1, obj2, ... (* wild card allowed)\n

    """
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    if not aprs_login:
        click.echo(ctx.get_help())
        click.echo("")
        ctx.fail("Must set --aprs-login or APRS_LOGIN")
        ctx.exit()

    if not aprs_password:
        click.echo(ctx.get_help())
        click.echo("")
        ctx.fail("Must set --aprs-password or APRS_PASSWORD")
        ctx.exit()

    # CONF.aprs_network.login = aprs_login
    # config["aprs"]["password"] = aprs_password

    LOG.info(f"APRSD Listen Started version: {aprsd.__version__}")

    CONF.log_opt_values(LOG, logging.DEBUG)
    collector.Collector()

    # Try and load saved MsgTrack list
    LOG.debug("Loading saved MsgTrack object.")

    # Initialize the client factory and create
    # The correct client object ready for use
    # Make sure we have 1 client transport enabled
    if not client_factory.is_client_enabled():
        LOG.error("No Clients are enabled in config.")
        sys.exit(-1)

    # Creates the client object
    LOG.info("Creating client connection")
    aprs_client = client_factory.create()
    LOG.info(aprs_client)

    LOG.debug(f"Filter by '{filter}'")
    aprs_client.set_filter(filter)

    keepalive = keep_alive.KeepAliveThread()
    # keepalive.start()

    if not CONF.enable_seen_list:
        # just deregister the class from the packet collector
        packet_collector.PacketCollector().unregister(seen_list.SeenList)

    # from aprsd.client import stats as client_stats
    # from aprsd.packets.packet_list import PacketList  # noqa: F401
    # from aprsd.packets.seen_list import SeenList  # noqa: F401
    # from aprsd.packets.tracker import PacketTrack  # noqa: F401
    # from aprsd.packets.watch_list import WatchList  # noqa: F401
    # from aprsd.plugins import email
    # from aprsd.threads import aprsd as aprsd_thread
    # c = collector.Collector()
    # # c.unregister_producer(app.APRSDStats)
    # c.unregister_producer(PacketList)
    # c.unregister_producer(WatchList)
    # #c.unregister_producer(PacketTrack)
    # c.unregister_producer(plugin.PluginManager)
    # c.unregister_producer(aprsd_thread.APRSDThreadList)
    # c.unregister_producer(email.EmailStats)
    # c.unregister_producer(client_stats.APRSClientStats)
    # c.unregister_producer(seen_list.SeenList)

    pm = None
    pm = plugin.PluginManager()
    if load_plugins:
        LOG.info("Loading plugins")
        pm.setup_plugins(load_help_plugin=False)
    else:
        LOG.warning(
            "Not Loading any plugins use --load-plugins to load what's "
            "defined in the config file.",
        )
    stats = stats_thread.APRSDStatsStoreThread()
    stats.start()

    LOG.debug("Create APRSDListenThread")
    listen_thread = APRSDListenThread(
        packet_queue=threads.packet_queue,
        packet_filter=packet_filter,
        plugin_manager=pm,
    )
    LOG.debug("Start APRSDListenThread")
    listen_thread.start()
    listen_stats = ListenStatsThread()
    listen_stats.start()

    keepalive.start()
    LOG.debug("keepalive Join")
    keepalive.join()
    LOG.debug("listen_thread Join")
    listen_thread.join()
    stats.join()
