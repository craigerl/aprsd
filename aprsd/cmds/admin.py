import logging
import os
import signal

import click
from oslo_config import cfg
import socketio

import aprsd
from aprsd import cli_helper
from aprsd import main as aprsd_main
from aprsd import utils
from aprsd.main import cli


os.environ["APRSD_ADMIN_COMMAND"] = "1"
# this import has to happen AFTER we set the
# above environment variable, so that the code
# inside the wsgi.py has the value
from aprsd import wsgi as aprsd_wsgi  # noqa


CONF = cfg.CONF
LOG = logging.getLogger("APRSD")


# main() ###
@cli.command()
@cli_helper.add_options(cli_helper.common_options)
@click.pass_context
@cli_helper.process_standard_options
def admin(ctx):
    """Start the aprsd admin interface."""
    signal.signal(signal.SIGINT, aprsd_main.signal_handler)
    signal.signal(signal.SIGTERM, aprsd_main.signal_handler)

    level, msg = utils._check_version()
    if level:
        LOG.warning(msg)
    else:
        LOG.info(msg)
    LOG.info(f"APRSD Started version: {aprsd.__version__}")
    # Dump all the config options now.
    CONF.log_opt_values(LOG, logging.DEBUG)

    async_mode = "threading"
    sio = socketio.Server(logger=True, async_mode=async_mode)
    aprsd_wsgi.app.wsgi_app = socketio.WSGIApp(sio, aprsd_wsgi.app.wsgi_app)
    aprsd_wsgi.init_app()
    sio.register_namespace(aprsd_wsgi.LoggingNamespace("/logs"))
    CONF.log_opt_values(LOG, logging.DEBUG)
    aprsd_wsgi.app.run(
        threaded=True,
        debug=False,
        port=CONF.admin.web_port,
        host=CONF.admin.web_ip,
    )
