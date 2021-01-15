import json
import logging

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
