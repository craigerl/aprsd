import json
import logging
import re

import requests

from aprsd import plugin, plugin_utils, trace


LOG = logging.getLogger("APRSD")


class USWeatherPlugin(plugin.APRSDRegexCommandPluginBase):
    """USWeather Command

    Returns a weather report for the calling weather station
    inside the United States only.  This uses the
    forecast.weather.gov API to fetch the weather.

    This service does not require an apiKey.

    How to Call: Send a message to aprsd
    "weather" - returns weather near the calling callsign
    """

    command_regex = "^[wW]"
    command_name = "USWeather"
    short_description = "Provide USA only weather of GPS Beacon location"

    @trace.trace
    def process(self, packet):
        LOG.info("Weather Plugin")
        fromcall = packet.get("from")
        # message = packet.get("message_text", None)
        # ack = packet.get("msgNo", "0")
        try:
            self.config.exists(["services", "aprs.fi", "apiKey"])
        except Exception as ex:
            LOG.error(f"Failed to find config aprs.fi:apikey {ex}")
            return "No aprs.fi apikey found"

        api_key = self.config["services"]["aprs.fi"]["apiKey"]
        try:
            aprs_data = plugin_utils.get_aprs_fi(api_key, fromcall)
        except Exception as ex:
            LOG.error(f"Failed to fetch aprs.fi data {ex}")
            return "Failed to fetch location"

        # LOG.debug("LocationPlugin: aprs_data = {}".format(aprs_data))
        lat = aprs_data["entries"][0]["lat"]
        lon = aprs_data["entries"][0]["lng"]

        try:
            wx_data = plugin_utils.get_weather_gov_for_gps(lat, lon)
        except Exception as ex:
            LOG.error(f"Couldn't fetch forecast.weather.gov '{ex}'")
            return "Unable to get weather"

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


class USMetarPlugin(plugin.APRSDRegexCommandPluginBase):
    """METAR Command

    This provides a METAR weather report from a station near the caller
    or callsign using the forecast.weather.gov api.  This only works
    for stations inside the United States.

    This service does not require an apiKey.

    How to Call: Send a message to aprsd
    "metar" - returns metar report near the calling callsign
    "metar CALLSIGN" - returns metar report near CALLSIGN

    """

    command_regex = "^[metar]"
    command_name = "USMetar"
    short_description = "USA only METAR of GPS Beacon location"

    @trace.trace
    def process(self, packet):
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

            try:
                self.config.exists(["services", "aprs.fi", "apiKey"])
            except Exception as ex:
                LOG.error(f"Failed to find config aprs.fi:apikey {ex}")
                return "No aprs.fi apikey found"

            api_key = self.config["services"]["aprs.fi"]["apiKey"]

            try:
                aprs_data = plugin_utils.get_aprs_fi(api_key, fromcall)
            except Exception as ex:
                LOG.error(f"Failed to fetch aprs.fi data {ex}")
                return "Failed to fetch location"

            # LOG.debug("LocationPlugin: aprs_data = {}".format(aprs_data))
            if not len(aprs_data["entries"]):
                LOG.error("Found no entries from aprs.fi!")
                return "Failed to fetch location"

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

    command_regex = "^[wW]"
    command_name = "OpenWeatherMap"
    short_description = "OpenWeatherMap weather of GPS Beacon location"

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
        fromcall = packet.get("from")
        message = packet.get("message_text", None)
        # ack = packet.get("msgNo", "0")
        LOG.info(f"OWMWeather Plugin '{message}'")
        a = re.search(r"^.*\s+(.*)", message)
        if a is not None:
            searchcall = a.group(1)
            searchcall = searchcall.upper()
        else:
            searchcall = fromcall

        try:
            self.config.exists(["services", "aprs.fi", "apiKey"])
        except Exception as ex:
            LOG.error(f"Failed to find config aprs.fi:apikey {ex}")
            return "No aprs.fi apikey found"

        api_key = self.config["services"]["aprs.fi"]["apiKey"]
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

        try:
            self.config.exists(["services", "openweathermap", "apiKey"])
        except Exception as ex:
            LOG.error(f"Failed to find config openweathermap:apiKey {ex}")
            return "No openweathermap apiKey found"

        try:
            self.config.exists(["aprsd", "units"])
        except Exception:
            LOG.debug("Couldn't find untis in aprsd:services:units")
            units = "metric"
        else:
            units = self.config["aprsd"]["units"]

        api_key = self.config["services"]["openweathermap"]["apiKey"]
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

    command_regex = "^[mM]"
    command_name = "AVWXWeather"
    short_description = "AVWX weather of GPS Beacon location"

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

        try:
            self.config.exists(["services", "aprs.fi", "apiKey"])
        except Exception as ex:
            LOG.error(f"Failed to find config aprs.fi:apikey {ex}")
            return "No aprs.fi apikey found"

        api_key = self.config["services"]["aprs.fi"]["apiKey"]
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

        try:
            self.config.exists(["services", "avwx", "apiKey"])
        except Exception as ex:
            LOG.error(f"Failed to find config avwx:apiKey {ex}")
            return "No avwx apiKey found"

        try:
            self.config.exists(self.config, ["services", "avwx", "base_url"])
        except Exception as ex:
            LOG.debug(f"Didn't find avwx:base_url {ex}")
            base_url = "https://avwx.rest"
        else:
            base_url = self.config["services"]["avwx"]["base_url"]

        api_key = self.config["services"]["avwx"]["apiKey"]
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
