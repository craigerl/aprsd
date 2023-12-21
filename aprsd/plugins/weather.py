import json
import logging
import re

from oslo_config import cfg
import requests

from aprsd import plugin, plugin_utils
from aprsd.utils import trace


CONF = cfg.CONF
LOG = logging.getLogger("APRSD")


class USWeatherPlugin(plugin.APRSDRegexCommandPluginBase, plugin.APRSFIKEYMixin):
    """USWeather Command

    Returns a weather report for the calling weather station
    inside the United States only.  This uses the
    forecast.weather.gov API to fetch the weather.

    This service does not require an apiKey.

    How to Call: Send a message to aprsd
    "weather" - returns weather near the calling callsign
    """

    # command_regex = r"^([w][x]|[w][x]\s|weather)"
    command_regex = r"^[wW]"

    command_name = "USWeather"
    short_description = "Provide USA only weather of GPS Beacon location"

    def setup(self):
        self.ensure_aprs_fi_key()

    @trace.trace
    def process(self, packet):
        LOG.info("Weather Plugin")
        fromcall = packet.from_call
        message = packet.get("message_text", None)
        # message = packet.get("message_text", None)
        # ack = packet.get("msgNo", "0")
        a = re.search(r"^.*\s+(.*)", message)
        if a is not None:
            searchcall = a.group(1)
            searchcall = searchcall.upper()
        else:
            searchcall = fromcall
        api_key = CONF.aprs_fi.apiKey
        try:
            aprs_data = plugin_utils.get_aprs_fi(api_key, searchcall)
        except Exception as ex:
            LOG.error(f"Failed to fetch aprs.fi data {ex}")
            return "Failed to fetch aprs.fi location"

        LOG.debug(f"LocationPlugin: aprs_data = {aprs_data}")
        if not len(aprs_data["entries"]):
            LOG.error("Didn't get any entries from aprs.fi")
            return "Failed to fetch aprs.fi location"

        lat = aprs_data["entries"][0]["lat"]
        lon = aprs_data["entries"][0]["lng"]

        try:
            wx_data = plugin_utils.get_weather_gov_for_gps(lat, lon)
        except Exception as ex:
            LOG.error(f"Couldn't fetch forecast.weather.gov '{ex}'")
            return "Unable to get weather"

        LOG.info(f"WX data {wx_data}")

        reply = (
            "%sF(%sF/%sF) %s. %s, %s."
            % (
                wx_data["currentobservation"]["Temp"],
                wx_data["data"]["temperature"][0],
                wx_data["data"]["temperature"][1],
                wx_data["data"]["weather"][0],
                wx_data["time"]["startPeriodName"][1],
                wx_data["data"]["weather"][1],
            )
        ).rstrip()
        LOG.debug(f"reply: '{reply}' ")
        return reply


class USMetarPlugin(plugin.APRSDRegexCommandPluginBase, plugin.APRSFIKEYMixin):
    """METAR Command

    This provides a METAR weather report from a station near the caller
    or callsign using the forecast.weather.gov api.  This only works
    for stations inside the United States.

    This service does not require an apiKey.

    How to Call: Send a message to aprsd
    "metar" - returns metar report near the calling callsign
    "metar CALLSIGN" - returns metar report near CALLSIGN

    """

    command_regex = r"^([m]|[M]|[m]\s|metar)"
    command_name = "USMetar"
    short_description = "USA only METAR of GPS Beacon location"

    def setup(self):
        self.ensure_aprs_fi_key()

    @trace.trace
    def process(self, packet):
        print("FISTY")
        fromcall = packet.get("from")
        message = packet.get("message_text", None)
        # ack = packet.get("msgNo", "0")
        LOG.info(f"WX Plugin '{message}'")
        a = re.search(r"^.*\s+(.*)", message)
        if a is not None:
            searchcall = a.group(1)
            station = searchcall.upper()
            try:
                resp = plugin_utils.get_weather_gov_metar(station)
            except Exception as e:
                LOG.debug(f"Weather failed with:  {str(e)}")
                reply = "Unable to find station METAR"
            else:
                station_data = json.loads(resp.text)
                reply = station_data["properties"]["rawMessage"]

            return reply
        else:
            # if no second argument, search for calling station
            fromcall = fromcall

            api_key = CONF.aprs_fi.apiKey

            try:
                aprs_data = plugin_utils.get_aprs_fi(api_key, fromcall)
            except Exception as ex:
                LOG.error(f"Failed to fetch aprs.fi data {ex}")
                return "Failed to fetch aprs.fi location"

            # LOG.debug("LocationPlugin: aprs_data = {}".format(aprs_data))
            if not len(aprs_data["entries"]):
                LOG.error("Found no entries from aprs.fi!")
                return "Failed to fetch aprs.fi location"

            lat = aprs_data["entries"][0]["lat"]
            lon = aprs_data["entries"][0]["lng"]

            try:
                wx_data = plugin_utils.get_weather_gov_for_gps(lat, lon)
            except Exception as ex:
                LOG.error(f"Couldn't fetch forecast.weather.gov '{ex}'")
                return "Unable to metar find station."

            if wx_data["location"]["metar"]:
                station = wx_data["location"]["metar"]
                try:
                    resp = plugin_utils.get_weather_gov_metar(station)
                except Exception as e:
                    LOG.debug(f"Weather failed with:  {str(e)}")
                    reply = "Failed to get Metar"
                else:
                    station_data = json.loads(resp.text)
                    reply = station_data["properties"]["rawMessage"]
            else:
                # Couldn't find a station
                reply = "No Metar station found"

        return reply


class OWMWeatherPlugin(plugin.APRSDRegexCommandPluginBase):
    """OpenWeatherMap Weather Command

    This provides weather near the caller or callsign.

    How to Call: Send a message to aprsd
    "weather" - returns the weather near the calling callsign
    "weather CALLSIGN" - returns the weather near CALLSIGN

    This plugin uses the openweathermap API to fetch
    location and weather information.

    To use this plugin you need to get an openweathermap
    account and apikey.

    https://home.openweathermap.org/api_keys

    """

    # command_regex = r"^([w][x]|[w][x]\s|weather)"
    command_regex = r"^[wW]"

    command_name = "OpenWeatherMap"
    short_description = "OpenWeatherMap weather of GPS Beacon location"

    def setup(self):
        if not CONF.owm_weather_plugin.apiKey:
            LOG.error("Config.owm_weather_plugin.apiKey is not set.  Disabling")
            self.enabled = False
        else:
            self.enabled = True

    def help(self):
        _help = [
            "openweathermap: Send {} to get weather "
            "from your location".format(self.command_regex),
            "openweathermap: Send {} <callsign> to get "
            "weather from <callsign>".format(self.command_regex),
        ]
        return _help

    @trace.trace
    def process(self, packet):
        fromcall = packet.get("from_call")
        message = packet.get("message_text", None)
        # ack = packet.get("msgNo", "0")
        LOG.info(f"OWMWeather Plugin '{message}'")
        a = re.search(r"^.*\s+(.*)", message)
        if a is not None:
            searchcall = a.group(1)
            searchcall = searchcall.upper()
        else:
            searchcall = fromcall

        api_key = CONF.aprs_fi.apiKey

        try:
            aprs_data = plugin_utils.get_aprs_fi(api_key, searchcall)
        except Exception as ex:
            LOG.error(f"Failed to fetch aprs.fi data {ex}")
            return "Failed to fetch location"

        # LOG.debug("LocationPlugin: aprs_data = {}".format(aprs_data))
        if not len(aprs_data["entries"]):
            LOG.error("Found no entries from aprs.fi!")
            return "Failed to fetch location"

        lat = aprs_data["entries"][0]["lat"]
        lon = aprs_data["entries"][0]["lng"]

        units = CONF.units
        api_key = CONF.owm_weather_plugin.apiKey
        try:
            wx_data = plugin_utils.fetch_openweathermap(
                api_key,
                lat,
                lon,
                units=units,
                exclude="minutely,hourly",
            )
        except Exception as ex:
            LOG.error(f"Couldn't fetch openweathermap api '{ex}'")
            # default to UTC
            return "Unable to get weather"

        if units == "metric":
            degree = "C"
        else:
            degree = "F"

        if "wind_gust" in wx_data["current"]:
            wind = "{:.0f}@{}G{:.0f}".format(
                wx_data["current"]["wind_speed"],
                wx_data["current"]["wind_deg"],
                wx_data["current"]["wind_gust"],
            )
        else:
            wind = "{:.0f}@{}".format(
                wx_data["current"]["wind_speed"],
                wx_data["current"]["wind_deg"],
            )

        # LOG.debug(wx_data["current"])
        # LOG.debug(wx_data["daily"])
        reply = "{} {:.1f}{}/{:.1f}{} Wind {} {}%".format(
            wx_data["current"]["weather"][0]["description"],
            wx_data["current"]["temp"],
            degree,
            wx_data["current"]["dew_point"],
            degree,
            wind,
            wx_data["current"]["humidity"],
        )

        return reply


class AVWXWeatherPlugin(plugin.APRSDRegexCommandPluginBase):
    """AVWXWeatherMap Weather Command

    Fetches a METAR weather report for the nearest
    weather station from the callsign
    Can be called with:
    metar - fetches metar for caller
    metar <CALLSIGN> - fetches metar for <CALLSIGN>

    This plugin requires the avwx-api service
    to provide the metar for a station near
    the callsign.

    avwx-api is an opensource project that has
    a hosted service here: https://avwx.rest/

    You can launch your own avwx-api in a container
    by cloning the githug repo here: https://github.com/avwx-rest/AVWX-API

    Then build the docker container with:
    docker build -f Dockerfile -t avwx-api:master .
    """

    command_regex = r"^([m]|[m]|[m]\s|metar)"
    command_name = "AVWXWeather"
    short_description = "AVWX weather of GPS Beacon location"

    def setup(self):
        if not CONF.avwx_plugin.base_url:
            LOG.error("Config avwx_plugin.base_url not specified.  Disabling")
            return False
        elif not CONF.avwx_plugin.apiKey:
            LOG.error("Config avwx_plugin.apiKey not specified. Disabling")
            return False
        else:
            return True

    def help(self):
        _help = [
            "avwxweather: Send {} to get weather "
            "from your location".format(self.command_regex),
            "avwxweather: Send {} <callsign> to get "
            "weather from <callsign>".format(self.command_regex),
        ]
        return _help

    @trace.trace
    def process(self, packet):
        fromcall = packet.get("from")
        message = packet.get("message_text", None)
        # ack = packet.get("msgNo", "0")
        LOG.info(f"AVWXWeather Plugin '{message}'")
        a = re.search(r"^.*\s+(.*)", message)
        if a is not None:
            searchcall = a.group(1)
            searchcall = searchcall.upper()
        else:
            searchcall = fromcall

        api_key = CONF.aprs_fi.apiKey
        try:
            aprs_data = plugin_utils.get_aprs_fi(api_key, searchcall)
        except Exception as ex:
            LOG.error(f"Failed to fetch aprs.fi data {ex}")
            return "Failed to fetch location"

        # LOG.debug("LocationPlugin: aprs_data = {}".format(aprs_data))
        if not len(aprs_data["entries"]):
            LOG.error("Found no entries from aprs.fi!")
            return "Failed to fetch location"

        lat = aprs_data["entries"][0]["lat"]
        lon = aprs_data["entries"][0]["lng"]

        api_key = CONF.avwx_plugin.apiKey
        base_url = CONF.avwx_plugin.base_url
        token = f"TOKEN {api_key}"
        headers = {"Authorization": token}
        try:
            coord = f"{lat},{lon}"
            url = (
                "{}/api/station/near/{}?"
                "n=1&airport=false&reporting=true&format=json".format(base_url, coord)
            )

            LOG.debug(f"Get stations near me '{url}'")
            response = requests.get(url, headers=headers)
        except Exception as ex:
            LOG.error(ex)
            raise Exception(f"Failed to get the weather '{ex}'")
        else:
            wx_data = json.loads(response.text)

        # LOG.debug(wx_data)
        station = wx_data[0]["station"]["icao"]

        try:
            url = (
                "{}/api/metar/{}?options=info,translate,summary"
                "&airport=true&reporting=true&format=json&onfail=cache".format(
                    base_url,
                    station,
                )
            )

            LOG.debug(f"Get METAR '{url}'")
            response = requests.get(url, headers=headers)
        except Exception as ex:
            LOG.error(ex)
            raise Exception(f"Failed to get metar {ex}")
        else:
            metar_data = json.loads(response.text)

        # LOG.debug(metar_data)
        return metar_data["raw"]
