#  Utilities for plugins to use
import logging

import requests

LOG = logging.getLogger("APRSD")


def get_aprs_fi(api_key, callsign):
    LOG.info("Fetch aprs.fi location for '{}'".format(callsign))
    try:
        url = (
            "http://api.aprs.fi/api/get?"
            "&what=loc&apikey={}&format=json"
            "&name={}".format(api_key, callsign)
        )
        response = requests.get(url)
    except Exception:
        raise Exception("Failed to get aprs.fi location")
    else:
        response.raise_for_status()
        return response


def get_weather_gov_for_gps(lat, lon):
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
        return response


def get_weather_gov_metar(station):
    LOG.debug("Fetch metar for station '{}'".format(station))
    try:
        url = "https://api.weather.gov/stations/{}/observations/latest".format(
            station,
        )
        response = requests.get(url)
    except Exception:
        raise Exception("Failed to fetch metar")
    else:
        response.raise_for_status()
        return response
