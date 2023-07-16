import logging

from oslo_config import cfg

from aprsd import admin_web
from aprsd import conf  # noqa


CONF = cfg.CONF
LOG = logging.getLogger("APRSD")
app = None
app = admin_web.create_app()
