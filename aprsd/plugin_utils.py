#  Utilities for plugins to use
import json
import logging

import requests


LOG = logging.getLogger("APRSD")


def get_aprs_fi(api_key, callsign):
    LOG.debug(f"Fetch aprs.fi location for '{callsign}'")
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
        return json.loads(response.text)


def get_weather_gov_for_gps(lat, lon):
    LOG.debug(f"Fetch station at {lat}, {lon}")
    try:
        url2 = (
            "https://forecast.weather.gov/MapClick.php?lat=%s"
            "&lon=%s&FcstType=json" % (lat, lon)
        )
        LOG.debug(f"Fetching weather '{url2}'")
        response = requests.get(url2)
    except Exception as e:
        LOG.error(e)
        raise Exception("Failed to get weather")
    else:
        response.raise_for_status()
        return json.loads(response.text)


def get_weather_gov_metar(station):
    LOG.debug(f"Fetch metar for station '{station}'")
    try:
        url = "https://api.weather.gov/stations/{}/observations/latest".format(
            station,
        )
        response = requests.get(url)
    except Exception:
        raise Exception("Failed to fetch metar")
    else:
        response.raise_for_status()
        return json.loads(response)


def fetch_openweathermap(api_key, lat, lon, units="metric", exclude=None):
    LOG.debug(f"Fetch openweathermap for {lat}, {lon}")
    if not exclude:
        exclude = "minutely,hourly,daily,alerts"
    try:
        url = (
            "https://api.openweathermap.org/data/2.5/onecall?"
            "lat={}&lon={}&appid={}&units={}&exclude={}".format(
                lat,
                lon,
                api_key,
                units,
                exclude,
            )
        )
        response = requests.get(url)
    except Exception as e:
        LOG.error(e)
        raise Exception("Failed to get weather")
    else:
        response.raise_for_status()
        return json.loads(response.text)
