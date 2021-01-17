import json
import logging
import re

from aprsd import plugin
import requests

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
            url = (
                "http://api.aprs.fi/api/get?"
                "&what=loc&apikey={}&format=json"
                "&name={}".format(api_key, fromcall)
            )
            response = requests.get(url)
            # aprs_data = json.loads(response.read())
            aprs_data = json.loads(response.text)
            lat = aprs_data["entries"][0]["lat"]
            lon = aprs_data["entries"][0]["lng"]
            url2 = (
                "https://forecast.weather.gov/MapClick.php?lat=%s"
                "&lon=%s&FcstType=json" % (lat, lon)
            )
            response2 = requests.get(url2)
            # wx_data = json.loads(response2.read())
            wx_data = json.loads(response2.text)
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
        except Exception as e:
            LOG.debug("Weather failed with:  " + "%s" % str(e))
            reply = "Unable to find you (send beacon?)"

        return reply


class WxPlugin(plugin.APRSDPluginBase):
    """METAR Command"""

    version = "1.0"
    command_regex = "^[wx]"
    command_name = "wx (Metar)"

    def get_aprs(self, fromcall):
        LOG.debug("Fetch aprs.fi location for '{}'".format(fromcall))
        api_key = self.config["aprs.fi"]["apiKey"]
        try:
            url = (
                "http://api.aprs.fi/api/get?"
                "&what=loc&apikey={}&format=json"
                "&name={}".format(api_key, fromcall)
            )
            response = requests.get(url)
        except Exception:
            raise Exception("Failed to get aprs.fi location")
        else:
            response.raise_for_status()
            return response

    def get_station(self, lat, lon):
        LOG.debug("Fetch station at {}, {}".format(lat, lon))
        try:
            url2 = (
                "https://forecast.weather.gov/MapClick.php?lat=%s"
                "&lon=%s&FcstType=json" % (lat, lon)
            )
            response = requests.get(url2)
        except Exception:
            raise Exception("Failed to get metar station")
        else:
            response.raise_for_status()
            return response

    def get_metar(self, station):
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

    def command(self, fromcall, message, ack):
        LOG.info("WX Plugin '{}'".format(message))
        a = re.search(r"^.*\s+(.*)", message)
        if a is not None:
            searchcall = a.group(1)
            station = searchcall.upper()
            try:
                resp = self.get_metar(station)
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
                resp = self.get_aprs(fromcall)
            except Exception as e:
                LOG.debug("Weather failed with:  {}".format(str(e)))
                reply = "Unable to find you (send beacon?)"
            else:
                aprs_data = json.loads(resp.text)
                lat = aprs_data["entries"][0]["lat"]
                lon = aprs_data["entries"][0]["lng"]

                try:
                    resp = self.get_station(lat, lon)
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
