import json
import logging
import re

from aprsd import plugin, plugin_utils, service

LOG = logging.getLogger("APRSD")


class WeatherPlugin(plugin.APRSDPluginBase):
    """Weather Command"""

    version = "1.0"
    command_regex = "^[wW]"
    command_name = "weather"

    def command(self, fromcall, message, ack):
        LOG.info("Weather Plugin")
        api_key = self.config["aprs.fi"]["apiKey"]

        # Fetching weather for someone else?
        a = re.search(r"^.*\s+(.*)", message)
        if a is not None:
            searchcall = a.group(1)
        else:
            searchcall = fromcall

        try:
            resp = plugin_utils.get_aprs_fi(api_key, searchcall)
        except Exception as e:
            LOG.debug("Weather failed with:  {}".format(str(e)))
            reply = "Unable to find you (send beacon?)"
        else:
            aprs_data = json.loads(resp.text)
            lat = aprs_data["entries"][0]["lat"]
            lon = aprs_data["entries"][0]["lng"]

            try:
                wx_service = service.WeatherService(self.config)
                reply = wx_service.forecast_short(lat, lon)
                # resp = plugin_utils.get_weather_gov_for_gps(lat, lon)
            except Exception as e:
                LOG.debug("Weather failed with:  {}".format(str(e)))
                return "Unable to Lookup weather"
            else:
                # wx_data = json.loads(resp.text)

                LOG.debug("reply: '{}' ".format(reply))
                return reply


class WxPlugin(WeatherPlugin):
    """METAR Command"""

    version = "1.0"
    command_regex = "^[mx]"
    command_name = "wx (Metar)"

    def command(self, fromcall, message, ack):
        LOG.info("WX Plugin '{}'".format(message))
        api_key = self.config["aprs.fi"]["apiKey"]
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
            try:
                resp = plugin_utils.get_aprs_fi(api_key, fromcall)
            except Exception as e:
                LOG.debug("Weather failed with:  {}".format(str(e)))
                reply = "Unable to find you (send beacon?)"
            else:
                aprs_data = json.loads(resp.text)
                lat = aprs_data["entries"][0]["lat"]
                lon = aprs_data["entries"][0]["lng"]

                try:
                    resp = self.get_weather_gov_for_gps(lat, lon)
                except Exception as e:
                    LOG.debug("Weather failed with:  {}".format(str(e)))
                    reply = "Unable to find you (send beacon?)"
                else:
                    wx_data = json.loads(resp.text)

                    if wx_data["location"]["metar"]:
                        station = wx_data["location"]["metar"]
                        try:
                            resp = self.get_metar(station)
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
