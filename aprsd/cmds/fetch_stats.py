# Fetch active stats from a remote running instance of aprsd admin web interface.
import logging

import click
import requests
from oslo_config import cfg
from rich.console import Console
from rich.table import Table

# local imports here
import aprsd
from aprsd import cli_helper
from aprsd.main import cli
from aprsd.threads.stats import StatsStore

# setup the global logger
# log.basicConfig(level=log.DEBUG) # level=10
LOG = logging.getLogger('APRSD')
CONF = cfg.CONF


@cli.command()
@cli_helper.add_options(cli_helper.common_options)
@click.option(
    '--host',
    type=str,
    default=None,
    help='IP address of the remote aprsd admin web ui fetch stats from.',
)
@click.option(
    '--port',
    type=int,
    default=None,
    help='Port of the remote aprsd web admin interface to fetch stats from.',
)
@click.pass_context
@cli_helper.process_standard_options
def fetch_stats(ctx, host, port):
    """Fetch stats from a APRSD admin web interface."""
    console = Console()
    console.print(f'APRSD Fetch-Stats started version: {aprsd.__version__}')

    CONF.log_opt_values(LOG, logging.DEBUG)
    if not host:
        host = CONF.admin.web_ip
    if not port:
        port = CONF.admin.web_port

    msg = f'Fetching stats from {host}:{port}'
    console.print(msg)
    with console.status(msg):
        response = requests.get(f'http://{host}:{port}/stats', timeout=120)
        if not response:
            console.print(
                f'Failed to fetch stats from {host}:{port}?',
                style='bold red',
            )
            return

        stats = response.json()
        if not stats:
            console.print(
                f'Failed to fetch stats from aprsd admin ui at {host}:{port}',
                style='bold red',
            )
            return

    aprsd_title = (
        'APRSD '
        f'[bold cyan]v{stats["APRSDStats"]["version"]}[/] '
        f'Callsign [bold green]{stats["APRSDStats"]["callsign"]}[/] '
        f'Uptime [bold yellow]{stats["APRSDStats"]["uptime"]}[/]'
    )

    console.rule(f'Stats from {host}:{port}')
    console.print('\n\n')
    console.rule(aprsd_title)

    # Show the connection to APRS
    # It can be a connection to an APRS-IS server or a local TNC via KISS or KISSTCP
    if 'aprs-is' in stats:
        title = f'APRS-IS Connection {stats["APRSClientStats"]["server_string"]}'
        table = Table(title=title)
        table.add_column('Key')
        table.add_column('Value')
        for key, value in stats['APRSClientStats'].items():
            table.add_row(key, value)
        console.print(table)

    threads_table = Table(title='Threads')
    threads_table.add_column('Name')
    threads_table.add_column('Alive?')
    for name, alive in stats['APRSDThreadList'].items():
        threads_table.add_row(name, str(alive))

    console.print(threads_table)

    packet_totals = Table(title='Packet Totals')
    packet_totals.add_column('Key')
    packet_totals.add_column('Value')
    packet_totals.add_row('Total Received', str(stats['PacketList']['rx']))
    packet_totals.add_row('Total Sent', str(stats['PacketList']['tx']))
    console.print(packet_totals)

    # Show each of the packet types
    packets_table = Table(title='Packets By Type')
    packets_table.add_column('Packet Type')
    packets_table.add_column('TX')
    packets_table.add_column('RX')
    for key, value in stats['PacketList']['packets'].items():
        packets_table.add_row(key, str(value['tx']), str(value['rx']))

    console.print(packets_table)

    if 'plugins' in stats:
        count = len(stats['PluginManager'])
        plugins_table = Table(title=f'Plugins ({count})')
        plugins_table.add_column('Plugin')
        plugins_table.add_column('Enabled')
        plugins_table.add_column('Version')
        plugins_table.add_column('TX')
        plugins_table.add_column('RX')
        plugins = stats['PluginManager']
        for key, _ in plugins.items():
            plugins_table.add_row(
                key,
                str(plugins[key]['enabled']),
                plugins[key]['version'],
                str(plugins[key]['tx']),
                str(plugins[key]['rx']),
            )

        console.print(plugins_table)

    if seen_list := stats.get('SeenList'):
        count = len(seen_list)
        seen_table = Table(title=f'Seen List ({count})')
        seen_table.add_column('Callsign')
        seen_table.add_column('Message Count')
        seen_table.add_column('Last Heard')
        for key, value in seen_list.items():
            seen_table.add_row(key, str(value['count']), value['last'])

        console.print(seen_table)

    if watch_list := stats.get('WatchList'):
        count = len(watch_list)
        watch_table = Table(title=f'Watch List ({count})')
        watch_table.add_column('Callsign')
        watch_table.add_column('Last Heard')
        for key, value in watch_list.items():
            watch_table.add_row(key, value['last'])

        console.print(watch_table)


@cli.command()
@cli_helper.add_options(cli_helper.common_options)
@click.option(
    '--raw',
    is_flag=True,
    default=False,
    help='Dump raw stats instead of formatted output.',
)
@click.option(
    '--show-section',
    default=['All'],
    help='Show specific sections of the stats. '
    ' Choices: All, APRSDStats, APRSDThreadList, APRSClientStats,'
    ' PacketList, SeenList, WatchList',
    multiple=True,
    type=click.Choice(
        [
            'All',
            'APRSDStats',
            'APRSDThreadList',
            'APRSClientStats',
            'PacketList',
            'SeenList',
            'WatchList',
        ],
        case_sensitive=False,
    ),
)
@click.pass_context
@cli_helper.process_standard_options
def dump_stats(ctx, raw, show_section):
    """Dump the current stats from the running APRSD instance."""
    console = Console()
    console.print(f'APRSD Dump-Stats started version: {aprsd.__version__}')

    with console.status('Dumping stats'):
        ss = StatsStore()
        ss.load()
        stats = ss.data
        if raw:
            if 'All' in show_section:
                console.print(stats)
                return
            else:
                for section in show_section:
                    console.print(f'Dumping {section} section:')
                    console.print(stats[section])
                return

        t = Table(title='APRSD Stats')
        t.add_column('Key')
        t.add_column('Value')
        for key, value in stats['APRSDStats'].items():
            t.add_row(key, str(value))

        if 'All' in show_section or 'APRSDStats' in show_section:
            console.print(t)

        # Show the thread list
        t = Table(title='Thread List')
        t.add_column('Name')
        t.add_column('Class')
        t.add_column('Alive?')
        t.add_column('Loop Count')
        t.add_column('Age')
        for name, value in stats['APRSDThreadList'].items():
            t.add_row(
                name,
                value['class'],
                str(value['alive']),
                str(value['loop_count']),
                str(value['age']),
            )

        if 'All' in show_section or 'APRSDThreadList' in show_section:
            console.print(t)

        # Show the plugins
        t = Table(title='Plugin List')
        t.add_column('Name')
        t.add_column('Enabled')
        t.add_column('Version')
        t.add_column('TX')
        t.add_column('RX')
        for name, value in stats['PluginManager'].items():
            t.add_row(
                name,
                str(value['enabled']),
                value['version'],
                str(value['tx']),
                str(value['rx']),
            )

        if 'All' in show_section or 'PluginManager' in show_section:
            console.print(t)

        # Now show the client stats
        t = Table(title='Client Stats')
        t.add_column('Key')
        t.add_column('Value')
        for key, value in stats['APRSClientStats'].items():
            t.add_row(key, str(value))

        if 'All' in show_section or 'APRSClientStats' in show_section:
            console.print(t)

        # now show the packet list
        packet_list = stats.get('PacketList')
        t = Table(title='Packet List')
        t.add_column('Key')
        t.add_column('Value')
        t.add_row('Total Received', str(packet_list['rx']))
        t.add_row('Total Sent', str(packet_list['tx']))

        if 'All' in show_section or 'PacketList' in show_section:
            console.print(t)

        # now show the seen list
        seen_list = stats.get('SeenList')
        sorted_seen_list = sorted(
            seen_list.items(),
        )
        t = Table(title='Seen List')
        t.add_column('Callsign')
        t.add_column('Message Count')
        t.add_column('Last Heard')
        for key, value in sorted_seen_list:
            t.add_row(
                key,
                str(value['count']),
                str(value['last']),
            )

        if 'All' in show_section or 'SeenList' in show_section:
            console.print(t)

        # now show the watch list
        watch_list = stats.get('WatchList')
        sorted_watch_list = sorted(
            watch_list.items(),
        )
        t = Table(title='Watch List')
        t.add_column('Callsign')
        t.add_column('Last Heard')
        for key, value in sorted_watch_list:
            t.add_row(
                key,
                str(value['last']),
            )

        if 'All' in show_section or 'WatchList' in show_section:
            console.print(t)
