import logging
import sys
import time

import aprslib
from aprslib.exceptions import LoginError
import click
from oslo_config import cfg

import aprsd
from aprsd import cli_helper, client, packets
from aprsd import conf  # noqa : F401
from aprsd.main import cli
from aprsd.threads import tx


CONF = cfg.CONF
LOG = logging.getLogger("APRSD")


@cli.command()
@cli_helper.add_options(cli_helper.common_options)
@click.option(
    "--aprs-login",
    envvar="APRS_LOGIN",
    show_envvar=True,
    help="What callsign to send the message from. Defaults to config entry.",
)
@click.option(
    "--aprs-password",
    envvar="APRS_PASSWORD",
    show_envvar=True,
    help="the APRS-IS password for APRS_LOGIN. Defaults to config entry.",
)
@click.option(
    "--no-ack",
    "-n",
    is_flag=True,
    show_default=True,
    default=False,
    help="Don't wait for an ack, just sent it to APRS-IS and bail.",
)
@click.option(
    "--wait-response",
    "-w",
    is_flag=True,
    show_default=True,
    default=False,
    help="Wait for a response to the message?",
)
@click.option("--raw", default=None, help="Send a raw message.  Implies --no-ack")
@click.argument("tocallsign", required=True)
@click.argument("command", nargs=-1, required=True)
@click.pass_context
@cli_helper.process_standard_options
def send_message(
    ctx,
    aprs_login,
    aprs_password,
    no_ack,
    wait_response,
    raw,
    tocallsign,
    command,
):
    """Send a message to a callsign via APRS_IS."""
    global got_ack, got_response
    quiet = ctx.obj["quiet"]

    if not aprs_login:
        if CONF.aprs_network.login == conf.client.DEFAULT_LOGIN:
            click.echo("Must set --aprs_login or APRS_LOGIN")
            ctx.exit(-1)
            return
        else:
            aprs_login = CONF.aprs_network.login

    if not aprs_password:
        LOG.warning(CONF.aprs_network.password)
        if not CONF.aprs_network.password:
            click.echo("Must set --aprs-password or APRS_PASSWORD")
            ctx.exit(-1)
            return
        else:
            aprs_password = CONF.aprs_network.password

    LOG.info(f"APRSD LISTEN Started version: {aprsd.__version__}")
    if type(command) is tuple:
        command = " ".join(command)
    if not quiet:
        if raw:
            LOG.info(f"L'{aprs_login}' R'{raw}'")
        else:
            LOG.info(f"L'{aprs_login}' To'{tocallsign}' C'{command}'")

    packets.PacketList()
    packets.WatchList()
    packets.SeenList()

    got_ack = False
    got_response = False

    def rx_packet(packet):
        global got_ack, got_response
        cl = client.factory.create()
        packet = cl.decode_packet(packet)
        packets.PacketList().rx(packet)
        packet.log("RX")
        # LOG.debug("Got packet back {}".format(packet))
        if isinstance(packet, packets.AckPacket):
            got_ack = True
        else:
            got_response = True
            from_call = packet.from_call
            our_call = CONF.callsign.lower()
            tx.send(
                packets.AckPacket(
                    from_call=our_call,
                    to_call=from_call,
                    msgNo=packet.msgNo,
                ),
                direct=True,
            )

        if got_ack:
            if wait_response:
                if got_response:
                    sys.exit(0)
            else:
                sys.exit(0)

    try:
        client.ClientFactory.setup()
        client.factory.create().client
    except LoginError:
        sys.exit(-1)

    # Send a message
    # then we setup a consumer to rx messages
    # We should get an ack back as well as a new message
    # we should bail after we get the ack and send an ack back for the
    # message
    if raw:
        tx.send(
            packets.Packet(from_call="", to_call="", raw=raw),
            direct=True,
        )
        sys.exit(0)
    else:
        tx.send(
            packets.MessagePacket(
                from_call=aprs_login,
                to_call=tocallsign,
                message_text=command,
            ),
            direct=True,
        )

    if no_ack:
        sys.exit(0)

    try:
        # This will register a packet consumer with aprslib
        # When new packets come in the consumer will process
        # the packet
        aprs_client = client.factory.create().client
        aprs_client.consumer(rx_packet, raw=False)
    except aprslib.exceptions.ConnectionDrop:
        LOG.error("Connection dropped, reconnecting")
        time.sleep(5)
        # Force the deletion of the client object connected to aprs
        # This will cause a reconnect, next time client.get_client()
        # is called
        aprs_client.reset()
