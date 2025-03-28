from typing import Callable, Protocol, runtime_checkable

from aprsd.packets import core
from aprsd.utils import singleton, trace


@runtime_checkable
class ClientDriver(Protocol):
    """Protocol for APRSD client drivers.

    This protocol defines the methods that must be
    implemented by APRSD client drivers.
    """

    @staticmethod
    def is_enabled(self) -> bool:
        pass

    @staticmethod
    def is_configured(self) -> bool:
        pass

    def is_alive(self) -> bool:
        pass

    def close(self) -> None:
        pass

    def send(self, packet: core.Packet) -> bool:
        pass

    def setup_connection(self) -> None:
        pass

    def set_filter(self, filter: str) -> None:
        pass

    def login_success(self) -> bool:
        pass

    def login_failure(self) -> str:
        pass

    def consumer(self, callback: Callable, raw: bool = False) -> None:
        pass

    def decode_packet(self, *args, **kwargs) -> core.Packet:
        pass

    def stats(self, serializable: bool = False) -> dict:
        pass


@singleton
class DriverRegistry(metaclass=trace.TraceWrapperMetaclass):
    """Registry for APRSD client drivers.

    This registry is used to register and unregister APRSD client drivers.

    This allows us to dynamically load the configured driver at runtime.

    All drivers are registered, then when aprsd needs the client, the
    registry provides the configured driver for the single instance of the
    single APRSD client.
    """

    def __init__(self):
        self.drivers = []

    def register(self, driver: Callable):
        if not isinstance(driver, ClientDriver):
            raise ValueError('Driver must be of ClientDriver type')
        self.drivers.append(driver)

    def unregister(self, driver: Callable):
        if driver in self.drivers:
            self.drivers.remove(driver)
        else:
            raise ValueError(f'Driver {driver} not found')

    def get_driver(self) -> ClientDriver:
        """Get the first enabled driver."""
        for driver in self.drivers:
            if driver.is_enabled() and driver.is_configured():
                return driver()
        raise ValueError('No enabled driver found')
