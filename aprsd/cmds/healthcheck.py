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
from aprsd import (  # noqa: F401
    cli_helper,
    conf,
)

# local imports here
from aprsd.main import cli
from aprsd.threads import stats as stats_threads

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
    ver_str = f"APRSD HealthCheck version: {aprsd.__version__}"
    console.log(ver_str)

    with console.status(ver_str):
        try:
            stats_obj = stats_threads.StatsStore()
            stats_obj.load()
            stats = stats_obj.data
            # console.print(stats)
        except Exception as ex:
            console.log(f"Failed to load stats: '{ex}'")
            sys.exit(-1)
        else:
            now = datetime.datetime.now()
            if not stats:
                console.log("No stats from aprsd")
                sys.exit(-1)

            email_stats = stats.get("EmailStats")
            if email_stats:
                email_thread_last_update = email_stats["last_check_time"]

                if email_thread_last_update != "never":
                    d = now - email_thread_last_update
                    max_timeout = {"hours": 0.0, "minutes": 5, "seconds": 30}
                    max_delta = datetime.timedelta(**max_timeout)
                    if d > max_delta:
                        console.log(f"Email thread is very old! {d}")
                        sys.exit(-1)

            client_stats = stats.get("APRSClientStats")
            if not client_stats:
                console.log("No APRSClientStats")
                sys.exit(-1)
            else:
                aprsis_last_update = client_stats["connection_keepalive"]
                d = now - aprsis_last_update
                max_timeout = {"hours": 0.0, "minutes": 5, "seconds": 0}
                max_delta = datetime.timedelta(**max_timeout)
                if d > max_delta:
                    LOG.error(f"APRS-IS last update is very old! {d}")
                    sys.exit(-1)

            console.log("OK")
            sys.exit(0)
