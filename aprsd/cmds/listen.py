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
from rich.console import Console

# local imports here
import aprsd
from aprsd import cli_helper, client, packets, stats, threads, utils
from aprsd.aprsd import cli
from aprsd.threads import rx


# setup the global logger
# logging.basicConfig(level=logging.DEBUG) # level=10
LOG = logging.getLogger("APRSD")
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
    def process_packet(self, *args, **kwargs):
        packet = self._client.decode_packet(*args, **kwargs)
        packet.log(header="RX Packet")


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
    config = ctx.obj["config"]

    if not aprs_login:
        click.echo(ctx.get_help())
        click.echo("")
        ctx.fail("Must set --aprs_login or APRS_LOGIN")
        ctx.exit()

    if not aprs_password:
        click.echo(ctx.get_help())
        click.echo("")
        ctx.fail("Must set --aprs-password or APRS_PASSWORD")
        ctx.exit()

    config["aprs"]["login"] = aprs_login
    config["aprs"]["password"] = aprs_password

    LOG.info(f"APRSD Listen Started version: {aprsd.__version__}")

    flat_config = utils.flatten_dict(config)
    LOG.info("Using CONFIG values:")
    for x in flat_config:
        if "password" in x or "aprsd.web.users.admin" in x:
            LOG.info(f"{x} = XXXXXXXXXXXXXXXXXXX")
        else:
            LOG.info(f"{x} = {flat_config[x]}")

    stats.APRSDStats(config)

    # Try and load saved MsgTrack list
    LOG.debug("Loading saved MsgTrack object.")
    packets.PacketTrack(config=config).load()
    packets.WatchList(config=config).load()
    packets.SeenList(config=config).load()

    # Initialize the client factory and create
    # The correct client object ready for use
    client.ClientFactory.setup(config)
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

    packets.PacketList(config=config)

    keepalive = threads.KeepAliveThread(config=config)
    keepalive.start()

    LOG.debug("Create APRSDListenThread")
    listen_thread = APRSDListenThread(threads.msg_queues, config=config)
    LOG.debug("Start APRSDListenThread")
    listen_thread.start()
    LOG.debug("keepalive Join")
    keepalive.join()
    LOG.debug("listen_thread Join")
    listen_thread.join()
