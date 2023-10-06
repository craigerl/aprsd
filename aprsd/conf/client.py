"""
The options for log setup
"""

from oslo_config import cfg


DEFAULT_LOGIN = "NOCALL"

aprs_group = cfg.OptGroup(
    name="aprs_network",
    title="APRS-IS Network settings",
)

kiss_serial_group = cfg.OptGroup(
    name="kiss_serial",
    title="KISS Serial device connection",
)

kiss_tcp_group = cfg.OptGroup(
    name="kiss_tcp",
    title="KISS TCP/IP Device connection",
)

fake_client_group = cfg.OptGroup(
    name="fake_client",
    title="Fake Client settings",
)
aprs_opts = [
    cfg.BoolOpt(
        "enabled",
        default=True,
        help="Set enabled to False if there is no internet connectivity."
             "This is useful for a direwolf KISS aprs connection only.",
    ),
    cfg.StrOpt(
        "login",
        default=DEFAULT_LOGIN,
        help="APRS Username",
    ),
    cfg.StrOpt(
        "password",
        secret=True,
        help="APRS Password "
             "Get the passcode for your callsign here: "
             "https://apps.magicbug.co.uk/passcode",
    ),
    cfg.HostAddressOpt(
        "host",
        default="noam.aprs2.net",
        help="The APRS-IS hostname",
    ),
    cfg.PortOpt(
        "port",
        default=14580,
        help="APRS-IS port",
    ),
]

kiss_serial_opts = [
    cfg.BoolOpt(
        "enabled",
        default=False,
        help="Enable Serial KISS interface connection.",
    ),
    cfg.StrOpt(
        "device",
        help="Serial Device file to use.  /dev/ttyS0",
    ),
    cfg.IntOpt(
        "baudrate",
        default=9600,
        help="The Serial device baud rate for communication",
    ),
    cfg.ListOpt(
        "path",
        default=["WIDE1-1", "WIDE2-1"],
        help="The APRS path to use for wide area coverage.",
    ),
]

kiss_tcp_opts = [
    cfg.BoolOpt(
        "enabled",
        default=False,
        help="Enable Serial KISS interface connection.",
    ),
    cfg.HostAddressOpt(
        "host",
        help="The KISS TCP Host to connect to.",
    ),
    cfg.PortOpt(
        "port",
        default=8001,
        help="The KISS TCP/IP network port",
    ),
    cfg.ListOpt(
        "path",
        default=["WIDE1-1", "WIDE2-1"],
        help="The APRS path to use for wide area coverage.",
    ),
]

fake_client_opts = [
    cfg.BoolOpt(
        "enabled",
        default=False,
        help="Enable fake client connection.",
    ),
]


def register_opts(config):
    config.register_group(aprs_group)
    config.register_opts(aprs_opts, group=aprs_group)
    config.register_group(kiss_serial_group)
    config.register_group(kiss_tcp_group)
    config.register_opts(kiss_serial_opts, group=kiss_serial_group)
    config.register_opts(kiss_tcp_opts, group=kiss_tcp_group)

    config.register_group(fake_client_group)
    config.register_opts(fake_client_opts, group=fake_client_group)


def list_opts():
    return {
        aprs_group.name: aprs_opts,
        kiss_serial_group.name: kiss_serial_opts,
        kiss_tcp_group.name: kiss_tcp_opts,
        fake_client_group.name: fake_client_opts,
    }
