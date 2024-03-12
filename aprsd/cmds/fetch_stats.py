# Fetch active stats from a remote running instance of aprsd server
# This uses the RPC server to fetch the stats from the remote server.

import logging

import click
from oslo_config import cfg
from rich.console import Console
from rich.table import Table

# local imports here
import aprsd
from aprsd import cli_helper
from aprsd.main import cli
from aprsd.rpc import client as rpc_client


# setup the global logger
# log.basicConfig(level=log.DEBUG) # level=10
LOG = logging.getLogger("APRSD")
CONF = cfg.CONF


@cli.command()
@cli_helper.add_options(cli_helper.common_options)
@click.option(
    "--host", type=str,
    default=None,
    help="IP address of the remote aprsd server to fetch stats from.",
)
@click.option(
    "--port", type=int,
    default=None,
    help="Port of the remote aprsd server rpc port to fetch stats from.",
)
@click.option(
    "--magic-word", type=str,
    default=None,
    help="Magic word of the remote aprsd server rpc port to fetch stats from.",
)
@click.pass_context
@cli_helper.process_standard_options
def fetch_stats(ctx, host, port, magic_word):
    """Fetch stats from a remote running instance of aprsd server."""
    LOG.info(f"APRSD Fetch-Stats started version: {aprsd.__version__}")

    CONF.log_opt_values(LOG, logging.DEBUG)
    if not host:
        host = CONF.rpc_settings.ip
    if not port:
        port = CONF.rpc_settings.port
    if not magic_word:
        magic_word = CONF.rpc_settings.magic_word

    msg = f"Fetching stats from {host}:{port} with magic word '{magic_word}'"
    console = Console()
    console.print(msg)
    with console.status(msg):
        client = rpc_client.RPCClient(host, port, magic_word)
        stats = client.get_stats_dict()
        if stats:
            console.print_json(data=stats)
        else:
            LOG.error(f"Failed to fetch stats via RPC aprsd server at {host}:{port}")
            return
    aprsd_title = (
        "APRSD "
        f"[bold cyan]v{stats['aprsd']['version']}[/] "
        f"Callsign [bold green]{stats['aprsd']['callsign']}[/] "
        f"Uptime [bold yellow]{stats['aprsd']['uptime']}[/]"
    )

    console.rule(f"Stats from {host}:{port} with magic word '{magic_word}'")
    console.print("\n\n")
    console.rule(aprsd_title)

    # Show the connection to APRS
    # It can be a connection to an APRS-IS server or a local TNC via KISS or KISSTCP
    if "aprs-is" in stats:
        title = f"APRS-IS Connection {stats['aprs-is']['server']}"
        table = Table(title=title)
        table.add_column("Key")
        table.add_column("Value")
        for key, value in stats["aprs-is"].items():
            table.add_row(key, value)
        console.print(table)

    threads_table = Table(title="Threads")
    threads_table.add_column("Name")
    threads_table.add_column("Alive?")
    for name, alive in stats["aprsd"]["threads"].items():
        threads_table.add_row(name, str(alive))

    console.print(threads_table)

    msgs_table = Table(title="Messages")
    msgs_table.add_column("Key")
    msgs_table.add_column("Value")
    for key, value in stats["messages"].items():
        msgs_table.add_row(key, str(value))

    console.print(msgs_table)

    packet_totals = Table(title="Packet Totals")
    packet_totals.add_column("Key")
    packet_totals.add_column("Value")
    packet_totals.add_row("Total Received", str(stats["packets"]["total_received"]))
    packet_totals.add_row("Total Sent", str(stats["packets"]["total_sent"]))
    packet_totals.add_row("Total Tracked", str(stats["packets"]["total_tracked"]))
    console.print(packet_totals)

    # Show each of the packet types
    packets_table = Table(title="Packets By Type")
    packets_table.add_column("Packet Type")
    packets_table.add_column("TX")
    packets_table.add_column("RX")
    for key, value in stats["packets"]["by_type"].items():
        packets_table.add_row(key, str(value["tx"]), str(value["rx"]))

    console.print(packets_table)

    if "plugins" in stats:
        count = len(stats["plugins"])
        plugins_table = Table(title=f"Plugins ({count})")
        plugins_table.add_column("Plugin")
        plugins_table.add_column("Enabled")
        plugins_table.add_column("Version")
        plugins_table.add_column("TX")
        plugins_table.add_column("RX")
        for key, value in stats["plugins"].items():
            plugins_table.add_row(
                key,
                str(stats["plugins"][key]["enabled"]),
                stats["plugins"][key]["version"],
                str(stats["plugins"][key]["tx"]),
                str(stats["plugins"][key]["rx"]),
            )

        console.print(plugins_table)

    if "seen_list" in stats["aprsd"]:
        count = len(stats["aprsd"]["seen_list"])
        seen_table = Table(title=f"Seen List ({count})")
        seen_table.add_column("Callsign")
        seen_table.add_column("Message Count")
        seen_table.add_column("Last Heard")
        for key, value in stats["aprsd"]["seen_list"].items():
            seen_table.add_row(key, str(value["count"]), value["last"])

        console.print(seen_table)

    if "watch_list" in stats["aprsd"]:
        count = len(stats["aprsd"]["watch_list"])
        watch_table = Table(title=f"Watch List ({count})")
        watch_table.add_column("Callsign")
        watch_table.add_column("Last Heard")
        for key, value in stats["aprsd"]["watch_list"].items():
            watch_table.add_row(key, value["last"])

        console.print(watch_table)
