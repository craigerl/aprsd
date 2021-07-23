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
import queue
import signal
import sys
import time

# local imports here
import aprsd
from aprsd import (
    client,
    email,
    flask,
    messaging,
    packets,
    plugin,
    stats,
    threads,
    trace,
    utils,
)
import aprslib
from aprslib.exceptions import LoginError
import click
import click_completion

# setup the global logger
# logging.basicConfig(level=logging.DEBUG) # level=10
LOG = logging.getLogger("APRSD")


CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])

flask_enabled = False

# server_event = threading.Event()

# localization, please edit:
# HOST = "noam.aprs2.net"     # north america tier2 servers round robin
# USER = "KM6XXX-9"           # callsign of this aprs client with SSID
# PASS = "99999"              # google how to generate this
# BASECALLSIGN = "KM6XXX"     # callsign of radio in the field to send email
# shortcuts = {
#   "aa" : "5551239999@vtext.com",
#   "cl" : "craiglamparter@somedomain.org",
#   "wb" : "5553909472@vtext.com"
# }


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
    "{:<12} {}".format(k, click_completion.core.shells[k])
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
    click.echo("{} completion installed in {}".format(shell, path))


def signal_handler(sig, frame):
    global flask_enabled

    threads.APRSDThreadList().stop_all()
    if "subprocess" not in str(frame):
        LOG.info(
            "Ctrl+C, Sending all threads exit! Can take up to 10 seconds {}".format(
                datetime.datetime.now(),
            ),
        )
        time.sleep(5)
        tracker = messaging.MsgTrack()
        tracker.save()
        LOG.info(stats.APRSDStats())
        # signal.signal(signal.SIGTERM, sys.exit(0))
        # sys.exit(0)
    if flask_enabled:
        signal.signal(signal.SIGTERM, sys.exit(0))


# Setup the logging faciility
# to disable logging to stdout, but still log to file
# use the --quiet option on the cmdln
def setup_logging(config, loglevel, quiet):
    log_level = utils.LOG_LEVELS[loglevel]
    LOG.setLevel(log_level)
    log_format = config["aprsd"].get("logformat", utils.DEFAULT_LOG_FORMAT)
    date_format = config["aprsd"].get("dateformat", utils.DEFAULT_DATE_FORMAT)
    log_formatter = logging.Formatter(fmt=log_format, datefmt=date_format)
    log_file = config["aprsd"].get("logfile", None)
    if log_file:
        fh = RotatingFileHandler(log_file, maxBytes=(10248576 * 5), backupCount=4)
    else:
        fh = NullHandler()

    fh.setFormatter(log_formatter)
    LOG.addHandler(fh)

    imap_logger = None
    if config["aprsd"]["email"].get("enabled", False) and config["aprsd"]["email"][
        "imap"
    ].get("debug", False):

        imap_logger = logging.getLogger("imapclient.imaplib")
        imap_logger.setLevel(log_level)
        imap_logger.addHandler(fh)

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
    default=utils.DEFAULT_CONFIG_FILE,
    help="The aprsd config file to use for options.",
)
def check_version(loglevel, config_file):
    config = utils.parse_config(config_file)

    # Force setting the config to the modules that need it
    # TODO(Walt): convert these modules to classes that can
    # Accept the config as a constructor param, instead of this
    # hacky global setting
    email.CONFIG = config

    setup_logging(config, loglevel, False)
    level, msg = utils._check_version()
    if level:
        LOG.warning(msg)
    else:
        LOG.info(msg)


@main.command()
def sample_config():
    """This dumps the config to stdout."""
    click.echo(utils.dump_default_cfg())


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
    default=utils.DEFAULT_CONFIG_FILE,
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

    config = utils.parse_config(config_file)
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
    LOG.info("APRSD Started version: {}".format(aprsd.__version__))
    if type(command) is tuple:
        command = " ".join(command)
    if not quiet:
        if raw:
            LOG.info("L'{}' R'{}'".format(aprs_login, raw))
        else:
            LOG.info("L'{}' To'{}' C'{}'".format(aprs_login, tocallsign, command))

    got_ack = False
    got_response = False

    def rx_packet(packet):
        global got_ack, got_response
        # LOG.debug("Got packet back {}".format(packet))
        resp = packet.get("response", None)
        if resp == "ack":
            ack_num = packet.get("msgNo")
            LOG.info("We got ack for our sent message {}".format(ack_num))
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
        cl = client.Client(config)
        cl.setup_connection()
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
        aprs_client = client.get_client()
        aprs_client.consumer(rx_packet, raw=False)
    except aprslib.exceptions.ConnectionDrop:
        LOG.error("Connection dropped, reconnecting")
        time.sleep(5)
        # Force the deletion of the client object connected to aprs
        # This will cause a reconnect, next time client.get_client()
        # is called
        cl.reset()


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
    "--disable-validation",
    is_flag=True,
    default=False,
    help="Disable email shortcut validation.  Bad email addresses can result in broken email responses!!",
)
@click.option(
    "-c",
    "--config",
    "config_file",
    show_default=True,
    default=utils.DEFAULT_CONFIG_FILE,
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
    disable_validation,
    config_file,
    flush,
):
    """Start the aprsd server process."""
    global flask_enabled
    signal.signal(signal.SIGINT, signal_handler)

    if not quiet:
        click.echo("Load config")

    config = utils.parse_config(config_file)

    # Force setting the config to the modules that need it
    # TODO(Walt): convert these modules to classes that can
    # Accept the config as a constructor param, instead of this
    # hacky global setting
    email.CONFIG = config

    setup_logging(config, loglevel, quiet)
    level, msg = utils._check_version()
    if level:
        LOG.warning(msg)
    else:
        LOG.info(msg)
    LOG.info("APRSD Started version: {}".format(aprsd.__version__))

    flat_config = utils.flatten_dict(config)
    LOG.info("Using CONFIG values:")
    for x in flat_config:
        if "password" in x or "aprsd.web.users.admin" in x:
            LOG.info("{} = XXXXXXXXXXXXXXXXXXX".format(x))
        else:
            LOG.info("{} = {}".format(x, flat_config[x]))

    if config["aprsd"].get("trace", False):
        trace.setup_tracing(["method", "api"])
    stats.APRSDStats(config)

    email_enabled = config["aprsd"]["email"].get("enabled", False)

    if email_enabled:
        # TODO(walt): Make email processing/checking optional?
        # Maybe someone only wants this to process messages with plugins only.
        valid = email.validate_email_config(config, disable_validation)
        if not valid:
            LOG.error("Failed to validate email config options")
            sys.exit(-1)
    else:
        LOG.info("Email services not enabled.")

    # Create the initial PM singleton and Register plugins
    plugin_manager = plugin.PluginManager(config)
    plugin_manager.setup_plugins()
    try:
        cl = client.Client(config)
        cl.client
    except LoginError:
        sys.exit(-1)

    # Now load the msgTrack from disk if any
    if flush:
        LOG.debug("Deleting saved MsgTrack.")
        messaging.MsgTrack().flush()
    else:
        # Try and load saved MsgTrack list
        LOG.debug("Loading saved MsgTrack object.")
        messaging.MsgTrack().load()

    rx_notify_queue = queue.Queue(maxsize=20)
    rx_msg_queue = queue.Queue(maxsize=20)
    tx_msg_queue = queue.Queue(maxsize=20)
    msg_queues = {
        "rx": rx_msg_queue,
        "tx": tx_msg_queue,
        "notify": rx_notify_queue,
    }

    rx_thread = threads.APRSDRXThread(msg_queues=msg_queues, config=config)
    tx_thread = threads.APRSDTXThread(msg_queues=msg_queues, config=config)
    if "watch_list" in config["aprsd"] and config["aprsd"]["watch_list"].get(
        "enabled",
        True,
    ):
        packets.PacketList(config)
        notify_thread = threads.APRSDNotifyThread(
            msg_queues=msg_queues,
            config=config,
        )
        notify_thread.start()

    if email_enabled:
        email_thread = email.APRSDEmailThread(msg_queues=msg_queues, config=config)
        email_thread.start()

    rx_thread.start()
    tx_thread.start()

    messaging.MsgTrack().restart()

    keepalive = threads.KeepAliveThread()
    keepalive.start()

    try:
        web_enabled = utils.check_config_option(config, ["aprsd", "web", "enabled"])
    except Exception:
        web_enabled = False

    if web_enabled:
        flask_enabled = True
        app = flask.init_flask(config, loglevel, quiet)
        app.run(
            host=config["aprsd"]["web"]["host"],
            port=config["aprsd"]["web"]["port"],
        )

    # If there are items in the msgTracker, then save them
    LOG.info("APRSD Exiting.")
    return 0


if __name__ == "__main__":
    main()
