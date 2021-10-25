#
# Listen on amateur radio aprs-is network for messages and respond to them.
# You must have an amateur radio callsign to use this software.  You must
# create an ~/.aprsd/config.yml file with all of the required settings.  To
# generate an example config.yml, just run aprsd, then copy the sample config
# to ~/.aprsd/config.yml and edit the settings.
#
# APRS messages:
#   l(ocation)             = descriptive location of calling station
#   w(eather)              = temp, (hi/low) forecast, later forecast
#   t(ime)                 = respond with the current time
#   f(ortune)              = respond with a short fortune
#   -email_addr email text = send an email
#   -2                     = display the last 2 emails received
#   p(ing)                 = respond with Pong!/time
#   anything else          = respond with usage
#
# (C)2018 Craig Lamparter
# License GPLv2
#

# python included libs
import datetime
import logging
from logging import NullHandler
from logging.handlers import RotatingFileHandler
import os
import signal
import sys
import time

import aprslib
from aprslib.exceptions import LoginError
import click
import click_completion

# local imports here
import aprsd
from aprsd import (
    flask, messaging, packets, plugin, stats, threads, trace, utils,
)
from aprsd import client
from aprsd import config as aprsd_config


# setup the global logger
# logging.basicConfig(level=logging.DEBUG) # level=10
LOG = logging.getLogger("APRSD")


CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])
flask_enabled = False


def custom_startswith(string, incomplete):
    """A custom completion match that supports case insensitive matching."""
    if os.environ.get("_CLICK_COMPLETION_COMMAND_CASE_INSENSITIVE_COMPLETE"):
        string = string.lower()
        incomplete = incomplete.lower()
    return string.startswith(incomplete)


click_completion.core.startswith = custom_startswith
click_completion.init()


cmd_help = """Shell completion for click-completion-command
Available shell types:
\b
  %s
Default type: auto
""" % "\n  ".join(
    f"{k:<12} {click_completion.core.shells[k]}"
    for k in sorted(click_completion.core.shells.keys())
)


@click.group(help=cmd_help, context_settings=CONTEXT_SETTINGS)
@click.version_option()
def main():
    pass


@main.command()
@click.option(
    "-i",
    "--case-insensitive/--no-case-insensitive",
    help="Case insensitive completion",
)
@click.argument(
    "shell",
    required=False,
    type=click_completion.DocumentedChoice(click_completion.core.shells),
)
def show(shell, case_insensitive):
    """Show the click-completion-command completion code"""
    extra_env = (
        {"_CLICK_COMPLETION_COMMAND_CASE_INSENSITIVE_COMPLETE": "ON"}
        if case_insensitive
        else {}
    )
    click.echo(click_completion.core.get_code(shell, extra_env=extra_env))


@main.command()
@click.option(
    "--append/--overwrite",
    help="Append the completion code to the file",
    default=None,
)
@click.option(
    "-i",
    "--case-insensitive/--no-case-insensitive",
    help="Case insensitive completion",
)
@click.argument(
    "shell",
    required=False,
    type=click_completion.DocumentedChoice(click_completion.core.shells),
)
@click.argument("path", required=False)
def install(append, case_insensitive, shell, path):
    """Install the click-completion-command completion"""
    extra_env = (
        {"_CLICK_COMPLETION_COMMAND_CASE_INSENSITIVE_COMPLETE": "ON"}
        if case_insensitive
        else {}
    )
    shell, path = click_completion.core.install(
        shell=shell,
        path=path,
        append=append,
        extra_env=extra_env,
    )
    click.echo(f"{shell} completion installed in {path}")


def signal_handler(sig, frame):
    global flask_enabled

    threads.APRSDThreadList().stop_all()
    if "subprocess" not in str(frame):
        LOG.info(
            "Ctrl+C, Sending all threads exit! Can take up to 10 seconds {}".format(
                datetime.datetime.now(),
            ),
        )
        time.sleep(1.5)
        messaging.MsgTrack().save()
        packets.WatchList().save()
        packets.SeenList().save()
        LOG.info(stats.APRSDStats())
        # signal.signal(signal.SIGTERM, sys.exit(0))
        # sys.exit(0)
    if flask_enabled:
        signal.signal(signal.SIGTERM, sys.exit(0))


# Setup the logging faciility
# to disable logging to stdout, but still log to file
# use the --quiet option on the cmdln
def setup_logging(config, loglevel, quiet):
    log_level = aprsd_config.LOG_LEVELS[loglevel]
    LOG.setLevel(log_level)
    log_format = config["aprsd"].get("logformat", aprsd_config.DEFAULT_LOG_FORMAT)
    date_format = config["aprsd"].get("dateformat", aprsd_config.DEFAULT_DATE_FORMAT)
    log_formatter = logging.Formatter(fmt=log_format, datefmt=date_format)
    log_file = config["aprsd"].get("logfile", None)
    if log_file:
        fh = RotatingFileHandler(log_file, maxBytes=(10248576 * 5), backupCount=4)
    else:
        fh = NullHandler()

    fh.setFormatter(log_formatter)
    LOG.addHandler(fh)

    imap_logger = None
    if config.get("aprsd.email.enabled", default=False) and config.get("aprsd.email.imap.debug", default=False):

        imap_logger = logging.getLogger("imapclient.imaplib")
        imap_logger.setLevel(log_level)
        imap_logger.addHandler(fh)

    if config.get("aprsd.web.enabled", default=False):
        qh = logging.handlers.QueueHandler(threads.logging_queue)
        q_log_formatter = logging.Formatter(
            fmt=aprsd_config.QUEUE_LOG_FORMAT,
            datefmt=aprsd_config.QUEUE_DATE_FORMAT,
        )
        qh.setFormatter(q_log_formatter)
        LOG.addHandler(qh)

    if not quiet:
        sh = logging.StreamHandler(sys.stdout)
        sh.setFormatter(log_formatter)
        LOG.addHandler(sh)
        if imap_logger:
            imap_logger.addHandler(sh)


@main.command()
@click.option(
    "--loglevel",
    default="INFO",
    show_default=True,
    type=click.Choice(
        ["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
        case_sensitive=False,
    ),
    show_choices=True,
    help="The log level to use for aprsd.log",
)
@click.option(
    "-c",
    "--config",
    "config_file",
    show_default=True,
    default=aprsd_config.DEFAULT_CONFIG_FILE,
    help="The aprsd config file to use for options.",
)
def check_version(loglevel, config_file):
    config = aprsd_config.parse_config(config_file)

    setup_logging(config, loglevel, False)
    level, msg = utils._check_version()
    if level:
        LOG.warning(msg)
    else:
        LOG.info(msg)


@main.command()
def sample_config():
    """This dumps the config to stdout."""
    click.echo(aprsd_config.dump_default_cfg())


@main.command()
@click.option(
    "--loglevel",
    default="DEBUG",
    show_default=True,
    type=click.Choice(
        ["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
        case_sensitive=False,
    ),
    show_choices=True,
    help="The log level to use for aprsd.log",
)
@click.option("--quiet", is_flag=True, default=False, help="Don't log to stdout")
@click.option(
    "-c",
    "--config",
    "config_file",
    show_default=True,
    default=aprsd_config.DEFAULT_CONFIG_FILE,
    help="The aprsd config file to use for options.",
)
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
@click.option("--raw", default=None, help="Send a raw message.  Implies --no-ack")
@click.argument("tocallsign", required=False)
@click.argument("command", nargs=-1, required=False)
def send_message(
    loglevel,
    quiet,
    config_file,
    aprs_login,
    aprs_password,
    no_ack,
    raw,
    tocallsign,
    command,
):
    """Send a message to a callsign via APRS_IS."""
    global got_ack, got_response

    config = aprsd_config.parse_config(config_file)
    if not aprs_login:
        click.echo("Must set --aprs_login or APRS_LOGIN")
        return

    if not aprs_password:
        click.echo("Must set --aprs-password or APRS_PASSWORD")
        return

    config["aprs"]["login"] = aprs_login
    config["aprs"]["password"] = aprs_password
    messaging.CONFIG = config

    setup_logging(config, loglevel, quiet)
    LOG.info(f"APRSD Started version: {aprsd.__version__}")
    if type(command) is tuple:
        command = " ".join(command)
    if not quiet:
        if raw:
            LOG.info(f"L'{aprs_login}' R'{raw}'")
        else:
            LOG.info(f"L'{aprs_login}' To'{tocallsign}' C'{command}'")

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

        if got_ack and got_response:
            sys.exit(0)

    try:
        client.ClientFactory.setup(config)
        client.factory.create().client
    except LoginError:
        sys.exit(-1)

    packets.PacketList(config=config)
    packets.WatchList(config=config)

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


# main() ###
@main.command()
@click.option(
    "--loglevel",
    default="INFO",
    show_default=True,
    type=click.Choice(
        ["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
        case_sensitive=False,
    ),
    show_choices=True,
    help="The log level to use for aprsd.log",
)
@click.option("--quiet", is_flag=True, default=False, help="Don't log to stdout")
@click.option(
    "-c",
    "--config",
    "config_file",
    show_default=True,
    default=aprsd_config.DEFAULT_CONFIG_FILE,
    help="The aprsd config file to use for options.",
)
@click.option(
    "-f",
    "--flush",
    "flush",
    is_flag=True,
    show_default=True,
    default=False,
    help="Flush out all old aged messages on disk.",
)
def server(
    loglevel,
    quiet,
    config_file,
    flush,
):
    """Start the aprsd server process."""
    global flask_enabled
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    if not quiet:
        click.echo("Load config")

    config = aprsd_config.parse_config(config_file)

    setup_logging(config, loglevel, quiet)
    level, msg = utils._check_version()
    if level:
        LOG.warning(msg)
    else:
        LOG.info(msg)
    LOG.info(f"APRSD Started version: {aprsd.__version__}")

    flat_config = utils.flatten_dict(config)
    LOG.info("Using CONFIG values:")
    for x in flat_config:
        if "password" in x or "aprsd.web.users.admin" in x:
            LOG.info(f"{x} = XXXXXXXXXXXXXXXXXXX")
        else:
            LOG.info(f"{x} = {flat_config[x]}")

    if config["aprsd"].get("trace", False):
        trace.setup_tracing(["method", "api"])
    stats.APRSDStats(config)

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

    # Now load the msgTrack from disk if any
    packets.PacketList(config=config)
    if flush:
        LOG.debug("Deleting saved MsgTrack.")
        messaging.MsgTrack(config=config).flush()
        packets.WatchList(config=config)
        packets.SeenList(config=config)
    else:
        # Try and load saved MsgTrack list
        LOG.debug("Loading saved MsgTrack object.")
        messaging.MsgTrack(config=config).load()
        packets.WatchList(config=config).load()
        packets.SeenList(config=config).load()

    # Create the initial PM singleton and Register plugins
    LOG.info("Loading Plugin Manager and registering plugins")
    plugin_manager = plugin.PluginManager(config)
    plugin_manager.setup_plugins()

    rx_thread = threads.APRSDRXThread(
        msg_queues=threads.msg_queues,
        config=config,
    )
    rx_thread.start()

    messaging.MsgTrack().restart()

    keepalive = threads.KeepAliveThread(config=config)
    keepalive.start()

    web_enabled = config.get("aprsd.web.enabled", default=False)

    if web_enabled:
        flask_enabled = True
        (socketio, app) = flask.init_flask(config, loglevel, quiet)
        socketio.run(
            app,
            host=config["aprsd"]["web"]["host"],
            port=config["aprsd"]["web"]["port"],
        )

    # If there are items in the msgTracker, then save them
    LOG.info("APRSD Exiting.")
    return 0


if __name__ == "__main__":
    main()
