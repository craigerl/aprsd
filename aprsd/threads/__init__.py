import queue

# Make these available to anyone importing
# aprsd.threads
from .aprsd import APRSDThread, APRSDThreadList  # noqa: F401
from .keep_alive import KeepAliveThread  # noqa: F401
from .rx import APRSDRXThread  # noqa: F401


rx_msg_queue = queue.Queue(maxsize=20)
msg_queues = {
    "rx": rx_msg_queue,
}
