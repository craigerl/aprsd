import queue

# Make these available to anyone importing
# aprsd.threads
from .aprsd import APRSDThread, APRSDThreadList  # noqa: F401
from .keep_alive import KeepAliveThread  # noqa: F401
from .rx import APRSDRXThread, APRSDDupeRXThread, APRSDProcessPacketThread  # noqa: F401


packet_queue = queue.Queue(maxsize=20)
