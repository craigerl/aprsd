import logging
import sys
import time

import aprslib
from aprslib.exceptions import LoginError
import click

import aprsd
from aprsd import cli_helper, client, messaging, packets

from ..aprsd import cli


LOG = logging.getLogger("APRSD")


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
    config = ctx.obj["config"]
    quiet = ctx.obj["quiet"]

    if not aprs_login:
        click.echo("Must set --aprs_login or APRS_LOGIN")
        return

    if not aprs_password:
        click.echo("Must set --aprs-password or APRS_PASSWORD")
        return

    config["aprs"]["login"] = aprs_login
    config["aprs"]["password"] = aprs_password

    LOG.info(f"APRSD LISTEN Started version: {aprsd.__version__}")
    if type(command) is tuple:
        command = " ".join(command)
    if not quiet:
        if raw:
            LOG.info(f"L'{aprs_login}' R'{raw}'")
        else:
            LOG.info(f"L'{aprs_login}' To'{tocallsign}' C'{command}'")

    packets.PacketList(config=config)
    packets.WatchList(config=config)
    packets.SeenList(config=config)

    got_ack = False
    got_response = False

    def rx_packet(packet):
        global got_ack, got_response
        # LOG.debug("Got packet back {}".format(packet))
        resp = packet.get("response", None)
        if resp == "ack":
            ack_num = packet.get("msgNo")
            LOG.info(f"We got ack for our sent message {ack_num}")
            messaging.log_packet(packet)
            got_ack = True
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
            got_response = True
            # Send the ack back?
            ack = messaging.AckMessage(
                config["aprs"]["login"],
                fromcall,
                msg_id=msg_number,
            )
            ack.send_direct()

        if got_ack:
            if wait_response:
                if got_response:
                    sys.exit(0)
            else:
                sys.exit(0)

    try:
        client.ClientFactory.setup(config)
        client.factory.create().client
    except LoginError:
        sys.exit(-1)

    # Send a message
    # then we setup a consumer to rx messages
    # We should get an ack back as well as a new message
    # we should bail after we get the ack and send an ack back for the
    # message
    if raw:
        msg = messaging.RawMessage(raw)
        msg.send_direct()
        sys.exit(0)
    else:
        msg = messaging.TextMessage(aprs_login, tocallsign, command)
    msg.send_direct()

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
