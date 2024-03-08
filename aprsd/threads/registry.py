import logging
import time

from oslo_config import cfg
import requests

import aprsd
from aprsd import threads as aprsd_threads


CONF = cfg.CONF
LOG = logging.getLogger("APRSD")


class APRSRegistryThread(aprsd_threads.APRSDThread):
    """This sends service information to the configured APRS Registry."""
    _loop_cnt: int = 1

    def __init__(self):
        super().__init__("APRSRegistryThread")
        self._loop_cnt = 1
        if not CONF.aprs_registry.enabled:
            LOG.error(
                "APRS Registry is not enabled.  ",
            )
            LOG.error(
                "APRS Registry thread is STOPPING.",
            )
            self.stop()
        LOG.info(
            "APRS Registry thread is running and will send "
            f"info every {CONF.aprs_registry.frequency_seconds} seconds "
            f"to {CONF.aprs_registry.registry_url}.",
        )

    def loop(self):
        # Only call the registry every N seconds
        if self._loop_cnt % CONF.aprs_registry.frequency_seconds == 0:
            info = {
                "callsign": CONF.callsign,
                "description": CONF.aprs_registry.description,
                "service_website": CONF.aprs_registry.service_website,
                "software": f"APRSD version {aprsd.__version__} "
                            "https://github.com/craigerl/aprsd",
            }
            try:
                requests.post(
                    f"{CONF.aprs_registry.registry_url}",
                    json=info,
                )
            except Exception as e:
                LOG.error(f"Failed to send registry info: {e}")

        time.sleep(1)
        self._loop_cnt += 1
        return True
