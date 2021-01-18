#  Base services class
# this is the service mechanism used to manage
# weather and location services from the config.
# There are many weather and location services
# that we could support.
import abc
import logging

from aprsd import utils, weather

LOG = logging.getLogger("APRSD")


class APRSDService(metaclass=abc.ABCMeta):

    config = None

    def __init__(self, config):
        LOG.debug("Service set config")
        self.config = config
        self.load()

    @abc.abstractmethod
    def load(self):
        """Load and configure the service"""
        pass


class WeatherService(APRSDService):
    _instance = None
    wx = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            # Put any init here
        return cls._instance

    def load(self):
        """Load the correct weather """
        wx_shortcut = self.config["aprsd"]["services"].get(
            "weather",
            weather.DEFAULT_PROVIDER,
        )
        wx_class = weather.PROVIDER_MAPPING[wx_shortcut]
        self.wx = utils.create_class(wx_class, weather.APRSDWeather, config=self.config)

    def forecast_short(self, lat, lon):
        return self.wx.forecast_short(lat, lon)

    def forecast_raw(self, lat, lon):
        return self.wx.forecast_raw(lat, lon)
