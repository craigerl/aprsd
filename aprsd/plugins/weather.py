import json
import logging
import re

from aprsd import plugin, plugin_utils, utils

LOG = logging.getLogger("APRSD")


class WeatherPlugin(plugin.APRSDPluginBase):
    """Weather Command"""

    version = "1.0"
    command_regex = "^[wW]"
    command_name = "weather"

    def command(self, fromcall, message, ack):
        LOG.info("Weather Plugin")
        api_key = self.config["aprs.fi"]["apiKey"]
        try:
            aprs_data = plugin_utils.get_aprs_fi(api_key, fromcall)
        except Exception as ex:
            LOG.error("Failed to fetch aprs.fi data {}".format(ex))
            return "Failed to fetch location"

        # LOG.debug("LocationPlugin: aprs_data = {}".format(aprs_data))
        lat = aprs_data["entries"][0]["lat"]
        lon = aprs_data["entries"][0]["lng"]

        try:
            wx_data = plugin_utils.get_weather_gov_for_gps(lat, lon)
        except Exception as ex:
            LOG.error("Couldn't fetch forecast.weather.gov '{}'".format(ex))
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
        LOG.debug("reply: '{}' ".format(reply))
        return reply


class USMetarPlugin(plugin.APRSDPluginBase):
    """METAR Command"""

    version = "1.0"
    command_regex = "^[metar]"
    command_name = "Metar"

    def command(self, fromcall, message, ack):
        LOG.info("WX Plugin '{}'".format(message))
        a = re.search(r"^.*\s+(.*)", message)
        if a is not None:
            searchcall = a.group(1)
            station = searchcall.upper()
            try:
                resp = plugin_utils.get_weather_gov_metar(station)
            except Exception as e:
                LOG.debug("Weather failed with:  {}".format(str(e)))
                reply = "Unable to find station METAR"
            else:
                station_data = json.loads(resp.text)
                reply = station_data["properties"]["rawMessage"]

            return reply
        else:
            # if no second argument, search for calling station
            fromcall = fromcall

            api_key = self.config["aprs.fi"]["apiKey"]
            try:
                aprs_data = plugin_utils.get_aprs_fi(api_key, fromcall)
            except Exception as ex:
                LOG.error("Failed to fetch aprs.fi data {}".format(ex))
                return "Failed to fetch location"

            # LOG.debug("LocationPlugin: aprs_data = {}".format(aprs_data))
            lat = aprs_data["entries"][0]["lat"]
            lon = aprs_data["entries"][0]["lng"]

            try:
                wx_data = plugin_utils.get_weather_gov_for_gps(lat, lon)
            except Exception as ex:
                LOG.error("Couldn't fetch forecast.weather.gov '{}'".format(ex))
                return "Unable to metar find station."

            if wx_data["location"]["metar"]:
                station = wx_data["location"]["metar"]
                try:
                    resp = plugin_utils.get_weather_gov_metar(station)
                except Exception as e:
                    LOG.debug("Weather failed with:  {}".format(str(e)))
                    reply = "Failed to get Metar"
                else:
                    station_data = json.loads(resp.text)
                    reply = station_data["properties"]["rawMessage"]
            else:
                # Couldn't find a station
                reply = "No Metar station found"

        return reply


class OWMWeatherPlugin(plugin.APRSDPluginBase):
    """OpenWeatherMap Weather Command"""

    version = "1.0"
    command_regex = "^[wW]"
    command_name = "Weather"

    def command(self, fromcall, message, ack):
        LOG.info("OWMWeather Plugin '{}'".format(message))
        a = re.search(r"^.*\s+(.*)", message)
        if a is not None:
            searchcall = a.group(1)
            searchcall = searchcall.upper()
        else:
            searchcall = fromcall

        api_key = self.config["aprs.fi"]["apiKey"]
        try:
            aprs_data = plugin_utils.get_aprs_fi(api_key, searchcall)
        except Exception as ex:
            LOG.error("Failed to fetch aprs.fi data {}".format(ex))
            return "Failed to fetch location"

        # LOG.debug("LocationPlugin: aprs_data = {}".format(aprs_data))
        lat = aprs_data["entries"][0]["lat"]
        lon = aprs_data["entries"][0]["lng"]

        try:
            utils.check_config_option(self.config, "openweathermap", "apiKey")
        except Exception as ex:
            LOG.error("Failed to find config openweathermap:apiKey {}".format(ex))
            return "No openweathermap apiKey found"

        try:
            utils.check_config_option(self.config, "aprsd", "units")
        except Exception:
            LOG.debug("Couldn't find untis in aprsd:services:units")
            units = "metric"
        else:
            units = self.config["aprsd"]["units"]

        api_key = self.config["openweathermap"]["apiKey"]
        try:
            wx_data = plugin_utils.fetch_openweathermap(
                api_key,
                lat,
                lon,
                units=units,
                exclude="minutely,hourly",
            )
        except Exception as ex:
            LOG.error("Couldn't fetch openweathermap api '{}'".format(ex))
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
