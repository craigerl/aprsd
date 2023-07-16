#
#  Used to fetch the stats url and determine if
#  aprsd server is 'healthy'
#
#
# python included libs
import datetime
import logging
import sys

import click
from oslo_config import cfg
from rich.console import Console

import aprsd
from aprsd import cli_helper, utils
from aprsd import conf  # noqa
# local imports here
from aprsd.main import cli
from aprsd.rpc import client as aprsd_rpc_client


# setup the global logger
# log.basicConfig(level=log.DEBUG) # level=10
CONF = cfg.CONF
LOG = logging.getLogger("APRSD")
console = Console()


@cli.command()
@cli_helper.add_options(cli_helper.common_options)
@click.option(
    "--timeout",
    show_default=True,
    default=3,
    help="How long to wait for healtcheck url to come back",
)
@click.pass_context
@cli_helper.process_standard_options
def healthcheck(ctx, timeout):
    """Check the health of the running aprsd server."""
    console.log(f"APRSD HealthCheck version: {aprsd.__version__}")
    if not CONF.rpc_settings.enabled:
        LOG.error("Must enable rpc_settings.enabled to use healthcheck")
        sys.exit(-1)
    if not CONF.rpc_settings.ip:
        LOG.error("Must enable rpc_settings.ip to use healthcheck")
        sys.exit(-1)
    if not CONF.rpc_settings.magic_word:
        LOG.error("Must enable rpc_settings.magic_word to use healthcheck")
        sys.exit(-1)

    with console.status(f"APRSD HealthCheck version: {aprsd.__version__}") as status:
        try:
            status.update(f"Contacting APRSD via RPC {CONF.rpc_settings.ip}")
            stats = aprsd_rpc_client.RPCClient().get_stats_dict()
        except Exception as ex:
            console.log(f"Failed to fetch healthcheck : '{ex}'")
            sys.exit(-1)
        else:
            if not stats:
                console.log("No stats from aprsd")
                sys.exit(-1)
            email_thread_last_update = stats["email"]["thread_last_update"]

            if email_thread_last_update != "never":
                delta = utils.parse_delta_str(email_thread_last_update)
                d = datetime.timedelta(**delta)
                max_timeout = {"hours": 0.0, "minutes": 5, "seconds": 0}
                max_delta = datetime.timedelta(**max_timeout)
                if d > max_delta:
                    console.log(f"Email thread is very old! {d}")
                    sys.exit(-1)

            aprsis_last_update = stats["aprs-is"]["last_update"]
            delta = utils.parse_delta_str(aprsis_last_update)
            d = datetime.timedelta(**delta)
            max_timeout = {"hours": 0.0, "minutes": 5, "seconds": 0}
            max_delta = datetime.timedelta(**max_timeout)
            if d > max_delta:
                LOG.error(f"APRS-IS last update is very old! {d}")
                sys.exit(-1)

            sys.exit(0)
