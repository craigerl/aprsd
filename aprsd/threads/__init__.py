import queue

# Make these available to anyone importing
# aprsd.threads
from .aprsd import APRSDThread, APRSDThreadList  # noqa: F401
from .rx import (  # noqa: F401
    APRSDProcessPacketThread,
    APRSDRXThread,
)
from .stats import APRSDStatsStoreThread, StatsLogThread  # noqa: F401

packet_queue = queue.Queue(maxsize=500)
