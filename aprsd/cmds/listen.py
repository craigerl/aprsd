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
from oslo_config import cfg
from rich.console import Console

# local imports here
import aprsd
from aprsd import cli_helper, client, packets, plugin, stats, threads
from aprsd.main import cli
from aprsd.rpc import server as rpc_server
from aprsd.threads import rx


# setup the global logger
# log.basicConfig(level=log.DEBUG) # level=10
LOG = logging.getLogger("APRSD")
CONF = cfg.CONF
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
        LOG.info(stats.APRSDStats())


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
            packets.GPSPacket.__name__: packets.GPSPacket,
            packets.MessagePacket.__name__: packets.MessagePacket,
            packets.MicEPacket.__name__: packets.MicEPacket,
            packets.WeatherPacket.__name__: packets.WeatherPacket,
        }

        if self.packet_filter:
            filter_class = filters[self.packet_filter]
            if isinstance(packet, filter_class):
                packet.log(header="RX")
                if self.plugin_manager:
                    # Don't do anything with the reply
                    # This is the listen only command.
                    self.plugin_manager.run(packet)
        else:
            if self.plugin_manager:
                # Don't do anything with the reply.
                # This is the listen only command.
                self.plugin_manager.run(packet)
            else:
                packet.log(header="RX")

        packets.PacketList().rx(packet)


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
            packets.Packet.__name__,
            packets.AckPacket.__name__,
            packets.GPSPacket.__name__,
            packets.MicEPacket.__name__,
            packets.MessagePacket.__name__,
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

    # Try and load saved MsgTrack list
    LOG.debug("Loading saved MsgTrack object.")

    # Initialize the client factory and create
    # The correct client object ready for use
    client.ClientFactory.setup()
    # Make sure we have 1 client transport enabled
    if not client.factory.is_client_enabled():
        LOG.error("No Clients are enabled in config.")
        sys.exit(-1)

    # Creates the client object
    LOG.info("Creating client connection")
    aprs_client = client.factory.create()
    LOG.info(aprs_client)

    LOG.debug(f"Filter by '{filter}'")
    aprs_client.set_filter(filter)

    keepalive = threads.KeepAliveThread()
    keepalive.start()

    if CONF.rpc_settings.enabled:
        rpc = rpc_server.APRSDRPCThread()
        rpc.start()

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

    LOG.debug("Create APRSDListenThread")
    listen_thread = APRSDListenThread(
        packet_queue=threads.packet_queue,
        packet_filter=packet_filter,
        plugin_manager=pm,
    )
    LOG.debug("Start APRSDListenThread")
    listen_thread.start()
    LOG.debug("keepalive Join")
    keepalive.join()
    LOG.debug("listen_thread Join")
    listen_thread.join()

    if CONF.rpc_settings.enabled:
        rpc.join()
