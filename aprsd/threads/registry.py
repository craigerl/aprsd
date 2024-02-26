import logging

from oslo_config import cfg
import requests

from aprsd import stats
from aprsd import threads as aprsd_threads


CONF = cfg.CONF
LOG = logging.getLogger("APRSD")

class APRSRegistryThread(aprsd_threads.APRSDThread):
    """This sends service information to the configured APRS Registry."""
    _loop_cnt: int = 1

    def __init__(self):
        super().__init__("APRSRegistryThread")
        self._loop_cnt = 1
        if not CONF.registry.enabled:
            LOG.error(
                "APRS Registry is not enabled.  ",
            )
            LOG.error(
                "APRS Registry thread is STOPPING.",
            )
            self.stop()

    def loop(self):
        # Only call the registry every N seconds
        if self._loop_cnt % CONF.registry.frequency_seconds == 0:
            info = {
                "callsign": CONF.callsign,
                "description": CONF.registry.description,
                "service_website": CONF.registry.service_website,
                "uptime": stats.APRSDStats().uptime,
            }
            try:
                requests.post(
                    f"{CONF.registry.registry_url}/api/v1/register",
                    json=info,
                )
            except Exception as e:
                LOG.error(f"Failed to send registry info: {e}")

        return True
