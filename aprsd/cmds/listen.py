#
# License GPLv2
#

# python included libs
import datetime
import logging
import sys
import time

import aprslib
import click

# local imports here
import aprsd
from aprsd import (
    cli_helper, client, messaging, packets, stats, threads, trace, utils,
)

from ..aprsd import cli


# setup the global logger
# logging.basicConfig(level=logging.DEBUG) # level=10
LOG = logging.getLogger("APRSD")


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
    messaging.MsgTrack(config=config).load()
    packets.WatchList(config=config).load()
    packets.SeenList(config=config).load()

    @trace.trace
    def rx_packet(packet):
        resp = packet.get("response", None)
        if resp == "ack":
            ack_num = packet.get("msgNo")
            LOG.info(f"We saw an ACK {ack_num} Ignoring")
            messaging.log_packet(packet)
        else:
            message = packet.get("message_text", None)
            fromcall = packet["from"]
            msg_number = packet.get("msgNo", "0")
            messaging.log_message(
                "Received Message",
                packet["raw"],
                message,
                fromcall=fromcall,
                ack=msg_number,
            )

    # Initialize the client factory and create
    # The correct client object ready for use
    client.ClientFactory.setup(config)
    # Make sure we have 1 client transport enabled
    if not client.factory.is_client_enabled():
        LOG.error("No Clients are enabled in config.")
        sys.exit(-1)

    # Creates the client object
    LOG.info("Creating client connection")
    client.factory.create().client
    aprs_client = client.factory.create().client

    LOG.debug(f"Filter by '{filter}'")
    aprs_client.set_filter(filter)

    while True:
        try:
            # This will register a packet consumer with aprslib
            # When new packets come in the consumer will process
            # the packet
            aprs_client.consumer(rx_packet, raw=False)
        except aprslib.exceptions.ConnectionDrop:
            LOG.error("Connection dropped, reconnecting")
            time.sleep(5)
            # Force the deletion of the client object connected to aprs
            # This will cause a reconnect, next time client.get_client()
            # is called
            aprs_client.reset()
        except aprslib.exceptions.UnknownFormat:
            LOG.error("Got a Bad packet")
