import queue

# Make these available to anyone importing
# aprsd.threads
from .aprsd import APRSDThread, APRSDThreadList
from .keep_alive import KeepAliveThread
from .rx import APRSDRXThread


rx_msg_queue = queue.Queue(maxsize=20)
msg_queues = {
    "rx": rx_msg_queue,
}
