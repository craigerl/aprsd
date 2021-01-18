import abc
import json
import logging

import requests

LOG = logging.getLogger("APRSD")

DEFAULT_PROVIDER = "us-gov"
PROVIDER_MAPPING = {
    "us-gov": "aprsd.weather.USWeatherGov",
}


class APRSDWeather(metaclass=abc.ABCMeta):
    confg = None

    def __init__(self, config):
        self.config = config

    @abc.abstractmethod
    def forecast_raw(self, lat, lon):
        """Get a raw forecast json for latitude, longitude.

        The format of the json response is entirely
        depentent on the service itself.
        """
        pass

    @abc.abstractmethod
    def forecast_short(self, lat, lon):
        """Get a short form forecast for latitude, longitude."""
        pass


class USWeatherGov(APRSDWeather):
    def forecast_raw(self, lat, lon):
        LOG.debug("Fetch station at {}, {}".format(lat, lon))
        try:
            url2 = (
                "https://forecast.weather.gov/MapClick.php?lat=%s"
                "&lon=%s&FcstType=json" % (lat, lon)
            )
            LOG.debug("Fetching weather '{}'".format(url2))
            response = requests.get(url2)
        except Exception as e:
            LOG.error(e)
            raise Exception("Failed to get weather")
        else:
            response.raise_for_status()
            return json.loads(response.text)

    def forecast_short(self, lat, lon):
        """Return a short string for the forecast."""
        wx_data = self.forecast_raw(lat, lon)
        reply = (
            "{}F({}F/{}F) {}. {}, {}.".format(
                wx_data["currentobservation"]["Temp"],
                wx_data["data"]["temperature"][0],
                wx_data["data"]["temperature"][1],
                wx_data["data"]["weather"][0],
                wx_data["time"]["startPeriodName"][1],
                wx_data["data"]["weather"][1],
            )
        ).rstrip()
        return reply
