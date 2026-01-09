#
# License GPLv2
#

# python included libs
import cProfile
import datetime
import logging
import pstats
import signal
import sys
import time

import click
import requests
from loguru import logger
from oslo_config import cfg
from rich.console import Console

# local imports here
import aprsd
from aprsd import cli_helper, packets, plugin, threads, utils
from aprsd.client.client import APRSDClient
from aprsd.main import cli
from aprsd.packets import core
from aprsd.packets import log as packet_log
from aprsd.packets.filter import PacketFilter
from aprsd.packets.filters import dupe_filter, packet_type
from aprsd.stats import collector
from aprsd.threads import keepalive, rx
from aprsd.threads import stats as stats_thread
from aprsd.threads.aprsd import APRSDThread
from aprsd.threads.stats import StatsLogThread

# setup the global logger
# log.basicConfig(level=log.DEBUG) # level=10
LOG = logging.getLogger('APRSD')
CONF = cfg.CONF
LOGU = logger
console = Console()


def signal_handler(sig, frame):
    threads.APRSDThreadList().stop_all()
    if 'subprocess' not in str(frame):
        LOG.info(
            'Ctrl+C, Sending all threads exit! Can take up to 10 seconds {}'.format(
                datetime.datetime.now(),
            ),
        )
        time.sleep(5)
        # Last save to disk
        collector.Collector().collect()


class APRSDListenProcessThread(rx.APRSDFilterThread):
    def __init__(
        self,
        packet_queue,
        packet_filter=None,
        plugin_manager=None,
        enabled_plugins=None,
        log_packets=False,
    ):
        super().__init__('ListenProcThread', packet_queue)
        self.packet_filter = packet_filter
        self.plugin_manager = plugin_manager
        if self.plugin_manager:
            LOG.info(f'Plugins {self.plugin_manager.get_message_plugins()}')
        self.log_packets = log_packets

    def print_packet(self, packet):
        if self.log_packets:
            packet_log.log(
                packet,
                packet_count=self.packet_count,
                force_log=True,
            )

    def process_packet(self, packet: type[core.Packet]):
        if self.plugin_manager:
            # Don't do anything with the reply.
            # This is the listen only command.
            self.plugin_manager.run(packet)


class StatsExportThread(APRSDThread):
    """Export stats to remote aprsd-exporter API."""

    def __init__(self, exporter_url):
        super().__init__('StatsExport')
        self.exporter_url = exporter_url
        self.period = 10  # Export stats every 60 seconds

    def loop(self):
        if self.loop_count % self.period == 0:
            try:
                # Collect all stats
                stats_json = collector.Collector().collect(serializable=True)
                # Remove the PacketList section to reduce payload size
                if 'PacketList' in stats_json:
                    del stats_json['PacketList']['packets']

                now = datetime.datetime.now()
                time_format = '%m-%d-%Y %H:%M:%S'
                stats = {
                    'time': now.strftime(time_format),
                    'stats': stats_json,
                }

                # Send stats to exporter API
                url = f'{self.exporter_url}/stats'
                headers = {'Content-Type': 'application/json'}
                response = requests.post(url, json=stats, headers=headers, timeout=10)

                if response.status_code == 200:
                    LOGU.info(f'Successfully exported stats to {self.exporter_url}')
                else:
                    LOGU.warning(
                        f'Failed to export stats to {self.exporter_url}: HTTP {response.status_code}'
                    )

            except requests.exceptions.RequestException as e:
                LOGU.error(f'Error exporting stats to {self.exporter_url}: {e}')
            except Exception as e:
                LOGU.error(f'Unexpected error in stats export: {e}')

        time.sleep(1)
        return True


@cli.command()
@cli_helper.add_options(cli_helper.common_options)
@click.option(
    '--aprs-login',
    envvar='APRS_LOGIN',
    show_envvar=True,
    help='What callsign to send the message from.',
)
@click.option(
    '--aprs-password',
    envvar='APRS_PASSWORD',
    show_envvar=True,
    help='the APRS-IS password for APRS_LOGIN',
)
@click.option(
    '--packet-filter',
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
    multiple=True,
    default=[],
    help='Filter by packet type',
)
@click.option(
    '--enable-plugin',
    multiple=True,
    help='Enable a plugin.  This is the name of the file in the plugins directory.',
)
@click.option(
    '--load-plugins',
    default=False,
    is_flag=True,
    help='Load plugins as enabled in aprsd.conf ?',
)
@click.argument(
    'filter',
    nargs=-1,
    required=True,
)
@click.option(
    '--log-packets',
    default=False,
    is_flag=True,
    help='Log incoming packets.',
)
@click.option(
    '--enable-packet-stats',
    default=False,
    is_flag=True,
    help='Enable packet stats periodic logging.',
)
@click.option(
    '--export-stats',
    default=False,
    is_flag=True,
    help='Export stats to remote aprsd-exporter API.',
)
@click.option(
    '--exporter-url',
    default='http://localhost:8081',
    help='URL of the aprsd-exporter API to send stats to.',
)
@click.option(
    '--profile',
    default=False,
    is_flag=True,
    help='Enable Python cProfile profiling to identify performance bottlenecks.',
)
@click.pass_context
@cli_helper.process_standard_options
def listen(
    ctx,
    aprs_login,
    aprs_password,
    packet_filter,
    enable_plugin,
    load_plugins,
    filter,
    log_packets,
    enable_packet_stats,
    export_stats,
    exporter_url,
    profile,
):
    """Listen to packets on the APRS-IS Network based on FILTER.

    FILTER is the APRS Filter to use.\n
     see http://www.aprs-is.net/javAPRSFilter.aspx\n
    r/lat/lon/dist - Range Filter Pass posits and objects within dist km from lat/lon.\n
    p/aa/bb/cc... - Prefix Filter Pass traffic with fromCall that start with aa or bb or cc.\n
    b/call1/call2... - Budlist Filter Pass all traffic from exact call: call1, call2, ... (* wild card allowed) \n
    o/obj1/obj2... - Object Filter Pass all objects with the exact name of obj1, obj2, ... (* wild card allowed)\n

    """
    # Initialize profiler if enabled
    profiler = None
    if profile:
        LOG.info('Starting Python cProfile profiling')
        profiler = cProfile.Profile()
        profiler.enable()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    if not aprs_login:
        click.echo(ctx.get_help())
        click.echo('')
        ctx.fail('Must set --aprs-login or APRS_LOGIN')
        ctx.exit()

    if not aprs_password:
        click.echo(ctx.get_help())
        click.echo('')
        ctx.fail('Must set --aprs-password or APRS_PASSWORD')
        ctx.exit()

    # CONF.aprs_network.login = aprs_login
    # config["aprs"]["password"] = aprs_password

    LOG.info(f'Python version: {sys.version}')
    LOG.info(f'APRSD Listen Started version: {aprsd.__version__}')
    utils.package.log_installed_extensions_and_plugins()

    CONF.log_opt_values(LOG, logging.DEBUG)
    collector.Collector()

    # Try and load saved MsgTrack list
    LOG.debug('Loading saved MsgTrack object.')

    # Initialize the client factory and create
    # The correct client object ready for use
    # Make sure we have 1 client transport enabled
    if not APRSDClient().is_enabled:
        LOG.error('No Clients are enabled in config.')
        sys.exit(-1)

    # Creates the client object
    LOG.info('Creating client connection')
    aprs_client = APRSDClient()
    LOG.info(aprs_client)
    if not aprs_client.login_success:
        # We failed to login, will just quit!
        msg = f'Login Failure: {aprs_client.login_failure}'
        LOG.error(msg)
        print(msg)
        sys.exit(-1)

    LOG.debug(f"Filter messages on aprsis server by '{filter}'")
    aprs_client.set_filter(filter)

    keepalive_thread = keepalive.KeepAliveThread()

    # we don't want the dupe filter to run here.
    PacketFilter().unregister(dupe_filter.DupePacketFilter)
    if packet_filter:
        LOG.info('Enabling packet filtering for {packet_filter}')
        packet_type.PacketTypeFilter().set_allow_list(packet_filter)
        PacketFilter().register(packet_type.PacketTypeFilter)
    else:
        LOG.info('No packet filtering enabled.')

    pm = None
    if load_plugins:
        pm = plugin.PluginManager()
        LOG.info('Loading plugins')
        pm.setup_plugins(load_help_plugin=False)
    elif enable_plugin:
        pm = plugin.PluginManager()
        pm.setup_plugins(
            load_help_plugin=False,
            plugin_list=enable_plugin,
        )
    else:
        LOG.warning(
            "Not Loading any plugins use --load-plugins to load what's "
            'defined in the config file.',
        )

    if pm:
        for p in pm.get_plugins():
            LOG.info('Loaded plugin %s', p.__class__.__name__)

    if log_packets:
        LOG.info('Packet Logging is enabled')
    else:
        LOG.info('Packet Logging is disabled')

    stats = stats_thread.APRSDStatsStoreThread()
    stats.start()

    LOG.debug('Start APRSDRxThread')
    rx_thread = rx.APRSDRXThread(packet_queue=threads.packet_queue)
    rx_thread.start()

    LOG.debug('Create APRSDListenProcessThread')
    listen_thread = APRSDListenProcessThread(
        packet_queue=threads.packet_queue,
        packet_filter=packet_filter,
        plugin_manager=pm,
        enabled_plugins=enable_plugin,
        log_packets=log_packets,
    )
    LOG.debug('Start APRSDListenProcessThread')
    listen_thread.start()

    LOG.debug(f'enable_packet_stats: {enable_packet_stats}')
    if enable_packet_stats:
        LOG.debug('Start StatsLogThread')
        listen_stats = StatsLogThread()
        listen_stats.start()

    LOG.debug(f'export_stats: {export_stats}')
    stats_export = None
    if export_stats:
        LOG.debug('Start StatsExportThread')
        stats_export = StatsExportThread(exporter_url)
        stats_export.start()

    keepalive_thread.start()
    LOG.debug('keepalive Join')
    keepalive_thread.join()
    rx_thread.join()
    listen_thread.join()
    stats.join()
    if stats_export:
        stats_export.join()

    # Save profiling results if enabled
    if profiler:
        profiler.disable()
        profile_file = 'aprsd_listen_profile.prof'
        profiler.dump_stats(profile_file)
        LOG.info(f'Profile saved to {profile_file}')

        # Print profiling summary
        LOG.info('Profile Summary (top 50 functions by cumulative time):')
        stats = pstats.Stats(profiler)
        stats.sort_stats('cumulative')

        # Log the top functions
        LOG.info('-' * 80)
        for item in stats.get_stats().items()[:50]:
            func_info, stats_tuple = item
            cumulative = stats_tuple[3]
            total_calls = stats_tuple[0]
            LOG.info(
                f'{func_info} - Calls: {total_calls}, Cumulative: {cumulative:.4f}s'
            )
