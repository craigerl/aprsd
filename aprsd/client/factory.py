import logging
from typing import Callable, Protocol, runtime_checkable

from aprsd import exception
from aprsd.packets import core

LOG = logging.getLogger("APRSD")


@runtime_checkable
class Client(Protocol):
    def __init__(self):
        pass

    def connect(self) -> bool:
        pass

    def disconnect(self) -> bool:
        pass

    def decode_packet(self, *args, **kwargs) -> type[core.Packet]:
        pass

    def is_enabled(self) -> bool:
        pass

    def is_configured(self) -> bool:
        pass

    def transport(self) -> str:
        pass

    def send(self, message: str) -> bool:
        pass

    def setup_connection(self) -> None:
        pass


class ClientFactory:
    _instance = None
    clients = []
    client = None

    def __new__(cls, *args, **kwargs):
        """This magic turns this into a singleton."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            # Put any initialization here.
        return cls._instance

    def __init__(self):
        self.clients: list[Callable] = []

    def register(self, aprsd_client: Callable):
        if isinstance(aprsd_client, Client):
            raise ValueError("Client must be a subclass of Client protocol")

        self.clients.append(aprsd_client)

    def create(self, key=None):
        for client in self.clients:
            if client.is_enabled():
                self.client = client()
                return self.client
        raise Exception("No client is configured!!")

    def client_exists(self):
        return bool(self.client)

    def is_client_enabled(self):
        """Make sure at least one client is enabled."""
        enabled = False
        for client in self.clients:
            if client.is_enabled():
                enabled = True
        return enabled

    def is_client_configured(self):
        enabled = False
        for client in self.clients:
            try:
                if client.is_configured():
                    enabled = True
            except exception.MissingConfigOptionException as ex:
                LOG.error(ex.message)
                return False
            except exception.ConfigOptionBogusDefaultException as ex:
                LOG.error(ex.message)
                return False
        return enabled
