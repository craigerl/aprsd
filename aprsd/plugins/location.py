import json
import logging
import re
import time

from aprsd import plugin
import requests

LOG = logging.getLogger("APRSD")


class LocationPlugin(plugin.APRSDPluginBase):
    """Location!"""

    version = "1.0"
    command_regex = "^[lL]"
    command_name = "location"

    config_items = {"apikey": "aprs.fi api key here"}

    def command(self, fromcall, message, ack):
        LOG.info("Location Plugin")
        # get last location of a callsign, get descriptive name from weather service
        api_key = self.config["aprs.fi"]["apiKey"]
        try:
            # optional second argument is a callsign to search
            a = re.search(r"^.*\s+(.*)", message)
            if a is not None:
                searchcall = a.group(1)
                searchcall = searchcall.upper()
            else:
                # if no second argument, search for calling station
                searchcall = fromcall
            url = (
                "http://api.aprs.fi/api/get?name="
                + searchcall
                + "&what=loc&apikey={}&format=json".format(api_key)
            )
            response = requests.get(url)
            # aprs_data = json.loads(response.read())
            aprs_data = json.loads(response.text)
            LOG.debug("LocationPlugin: aprs_data = {}".format(aprs_data))
            lat = aprs_data["entries"][0]["lat"]
            lon = aprs_data["entries"][0]["lng"]
            try:  # altitude not always provided
                alt = aprs_data["entries"][0]["altitude"]
            except Exception:
                alt = 0
            altfeet = int(alt * 3.28084)
            aprs_lasttime_seconds = aprs_data["entries"][0]["lasttime"]
            # aprs_lasttime_seconds = aprs_lasttime_seconds.encode(
            #    "ascii", errors="ignore"
            # )  # unicode to ascii
            delta_seconds = time.time() - int(aprs_lasttime_seconds)
            delta_hours = delta_seconds / 60 / 60
            url2 = (
                "https://forecast.weather.gov/MapClick.php?lat="
                + str(lat)
                + "&lon="
                + str(lon)
                + "&FcstType=json"
            )
            response2 = requests.get(url2)
            wx_data = json.loads(response2.text)

            reply = "{}: {} {}' {},{} {}h ago".format(
                searchcall,
                wx_data["location"]["areaDescription"],
                str(altfeet),
                str(lat),
                str(lon),
                str("%.1f" % round(delta_hours, 1)),
            ).rstrip()
        except Exception as e:
            LOG.debug("Locate failed with:  " + "%s" % str(e))
            reply = "Unable to find station " + searchcall + ".  Sending beacons?"

        return reply
