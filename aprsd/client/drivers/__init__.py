# All client drivers must be registered here
from aprsd.client.drivers.aprsis import APRSISDriver
from aprsd.client.drivers.fake import APRSDFakeDriver
from aprsd.client.drivers.registry import DriverRegistry
from aprsd.client.drivers.tcpkiss import TCPKISSDriver

driver_registry = DriverRegistry()
driver_registry.register(APRSDFakeDriver)
driver_registry.register(APRSISDriver)
driver_registry.register(TCPKISSDriver)
