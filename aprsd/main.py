# -*- coding: utf-8 -*-
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
import logging
import os
import signal
import sys
import time
from logging import NullHandler
from logging.handlers import RotatingFileHandler

import aprslib
import click
import click_completion
import yaml

# local imports here
import aprsd
from aprsd import client, email, messaging, plugin, utils

# setup the global logger
# logging.basicConfig(level=logging.DEBUG) # level=10
LOG = logging.getLogger("APRSD")

LOG_LEVELS = {
    "CRITICAL": logging.CRITICAL,
    "ERROR": logging.ERROR,
    "WARNING": logging.WARNING,
    "INFO": logging.INFO,
    "DEBUG": logging.DEBUG,
}

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


@click.group(help=cmd_help)
@click.version_option()
def main():
    pass


@main.command()
@click.option(
    "-i", "--case-insensitive/--no-case-insensitive", help="Case insensitive completion"
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
    "--append/--overwrite", help="Append the completion code to the file", default=None
)
@click.option(
    "-i", "--case-insensitive/--no-case-insensitive", help="Case insensitive completion"
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
        shell=shell, path=path, append=append, extra_env=extra_env
    )
    click.echo("%s completion installed in %s" % (shell, path))


def signal_handler(signal, frame):
    LOG.info("Ctrl+C, exiting.")
    # sys.exit(0)  # thread ignores this
    os._exit(0)


# end signal_handler


# Setup the logging faciility
# to disable logging to stdout, but still log to file
# use the --quiet option on the cmdln
def setup_logging(config, loglevel, quiet):
    log_level = LOG_LEVELS[loglevel]
    LOG.setLevel(log_level)
    log_format = "[%(asctime)s] [%(threadName)-12s] [%(levelname)-5.5s]" " %(message)s"
    date_format = "%m/%d/%Y %I:%M:%S %p"
    log_formatter = logging.Formatter(fmt=log_format, datefmt=date_format)
    log_file = config["aprs"].get("logfile", None)
    if log_file:
        fh = RotatingFileHandler(log_file, maxBytes=(10248576 * 5), backupCount=4)
    else:
        fh = NullHandler()

    fh.setFormatter(log_formatter)
    LOG.addHandler(fh)

    if not quiet:
        sh = logging.StreamHandler(sys.stdout)
        sh.setFormatter(log_formatter)
        LOG.addHandler(sh)


def process_packet(packet):
    """Process a packet recieved from aprs-is server."""

    LOG.debug("Process packet!")
    try:
        LOG.debug("Got message: {}".format(packet))

        fromcall = packet["from"]
        message = packet.get("message_text", None)
        if not message:
            LOG.debug("Didn't get a message, could be an ack?")
            if packet.get("response", None) == "ack":
                # looks like an ACK
                ack_num = packet.get("msgNo")
                messaging.ack_dict.update({ack_num: 1})

        msg_number = packet.get("msgNo", None)
        if msg_number:
            ack = msg_number
        else:
            ack = "0"

        messaging.log_message(
            "Received Message", packet["raw"], message, fromcall=fromcall, ack=ack
        )

        found_command = False
        # Get singleton of the PM
        pm = plugin.PluginManager()
        try:
            results = pm.run(fromcall=fromcall, message=message, ack=ack)
            for reply in results:
                found_command = True
                # A plugin can return a null message flag which signals
                # us that they processed the message correctly, but have
                # nothing to reply with, so we avoid replying with a usage string
                if reply is not messaging.NULL_MESSAGE:
                    LOG.debug("Sending '{}'".format(reply))
                    messaging.send_message(fromcall, reply)
                else:
                    LOG.debug("Got NULL MESSAGE from plugin")

            if not found_command:
                plugins = pm.get_plugins()
                names = [x.command_name for x in plugins]
                names.sort()

                reply = "Usage: {}".format(", ".join(names))
                messaging.send_message(fromcall, reply)
        except Exception as ex:
            LOG.exception("Plugin failed!!!", ex)
            reply = "A Plugin failed! try again?"
            messaging.send_message(fromcall, reply)

        # let any threads do their thing, then ack
        # send an ack last
        messaging.send_ack(fromcall, ack)
        LOG.debug("Packet processing complete")

    except (aprslib.ParseError, aprslib.UnknownFormat) as exp:
        LOG.exception("Failed to parse packet from aprs-is", exp)


@main.command()
def sample_config():
    """This dumps the config to stdout."""
    click.echo(yaml.dump(utils.DEFAULT_CONFIG_DICT))


@main.command()
@click.option(
    "--loglevel",
    default="DEBUG",
    show_default=True,
    type=click.Choice(
        ["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"], case_sensitive=False
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
@click.argument("tocallsign")
@click.argument("command", default="location")
def send_message(
    loglevel, quiet, config_file, aprs_login, aprs_password, tocallsign, command
):
    """Send a message to a callsign via APRS_IS."""
    click.echo("{} {} {} {}".format(aprs_login, aprs_password, tocallsign, command))

    click.echo("Load config")
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

    def rx_packet(packet):
        LOG.debug("Got packet back {}".format(packet))
        messaging.log_packet(packet)
        resp = packet.get("response", None)
        if resp == "ack":
            sys.exit(0)

    cl = client.Client(config)
    messaging.send_message_direct(tocallsign, command)

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
    default="DEBUG",
    show_default=True,
    type=click.Choice(
        ["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"], case_sensitive=False
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
def server(loglevel, quiet, disable_validation, config_file):
    """Start the aprsd server process."""

    signal.signal(signal.SIGINT, signal_handler)

    click.echo("Load config")
    config = utils.parse_config(config_file)

    # Force setting the config to the modules that need it
    # TODO(Walt): convert these modules to classes that can
    # Accept the config as a constructor param, instead of this
    # hacky global setting
    email.CONFIG = config
    messaging.CONFIG = config

    setup_logging(config, loglevel, quiet)
    LOG.info("APRSD Started version: {}".format(aprsd.__version__))

    # TODO(walt): Make email processing/checking optional?
    # Maybe someone only wants this to process messages with plugins only.
    valid = email.validate_email_config(config, disable_validation)
    if not valid:
        LOG.error("Failed to validate email config options")
        sys.exit(-1)

    # start the email thread
    email.start_thread()

    # Create the initial PM singleton and Register plugins
    plugin_manager = plugin.PluginManager(config)
    plugin_manager.setup_plugins()
    cl = client.Client(config)

    # setup and run the main blocking loop
    while True:
        # Now use the helper which uses the singleton
        aprs_client = client.get_client()

        # setup the consumer of messages and block until a messages
        try:
            # This will register a packet consumer with aprslib
            # When new packets come in the consumer will process
            # the packet
            aprs_client.consumer(process_packet, raw=False)
        except aprslib.exceptions.ConnectionDrop:
            LOG.error("Connection dropped, reconnecting")
            time.sleep(5)
            # Force the deletion of the client object connected to aprs
            # This will cause a reconnect, next time client.get_client()
            # is called
            cl.reset()


if __name__ == "__main__":
    main()
