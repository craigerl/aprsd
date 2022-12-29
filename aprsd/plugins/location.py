import logging
import re
import time

from oslo_config import cfg

from aprsd import packets, plugin, plugin_utils
from aprsd.utils import trace


CONF = cfg.CONF
LOG = logging.getLogger("APRSD")


class LocationPlugin(plugin.APRSDRegexCommandPluginBase, plugin.APRSFIKEYMixin):
    """Location!"""

    command_regex = r"^([l]|[l]\s|location)"
    command_name = "location"
    short_description = "Where in the world is a CALLSIGN's last GPS beacon?"

    def setup(self):
        self.ensure_aprs_fi_key()

    @trace.trace
    def process(self, packet: packets.MessagePacket):
        LOG.info("Location Plugin")
        fromcall = packet.from_call
        message = packet.get("message_text", None)

        api_key = CONF.aprs_fi.apiKey

        # optional second argument is a callsign to search
        a = re.search(r"^.*\s+(.*)", message)
        if a is not None:
            searchcall = a.group(1)
            searchcall = searchcall.upper()
        else:
            # if no second argument, search for calling station
            searchcall = fromcall

        try:
            aprs_data = plugin_utils.get_aprs_fi(api_key, searchcall)
        except Exception as ex:
            LOG.error(f"Failed to fetch aprs.fi '{ex}'")
            return "Failed to fetch aprs.fi location"

        LOG.debug(f"LocationPlugin: aprs_data = {aprs_data}")
        if not len(aprs_data["entries"]):
            LOG.error("Didn't get any entries from aprs.fi")
            return "Failed to fetch aprs.fi location"

        lat = aprs_data["entries"][0]["lat"]
        lon = aprs_data["entries"][0]["lng"]
        try:  # altitude not always provided
            alt = float(aprs_data["entries"][0]["altitude"])
        except Exception:
            alt = 0
        altfeet = int(alt * 3.28084)
        aprs_lasttime_seconds = aprs_data["entries"][0]["lasttime"]
        # aprs_lasttime_seconds = aprs_lasttime_seconds.encode(
        #    "ascii", errors="ignore"
        # )  # unicode to ascii
        delta_seconds = time.time() - int(aprs_lasttime_seconds)
        delta_hours = delta_seconds / 60 / 60

        try:
            wx_data = plugin_utils.get_weather_gov_for_gps(lat, lon)
        except Exception as ex:
            LOG.error(f"Couldn't fetch forecast.weather.gov '{ex}'")
            wx_data = {"location": {"areaDescription": "Unknown Location"}}

        if "location" not in wx_data:
            LOG.error(f"Couldn't fetch forecast.weather.gov '{wx_data}'")
            wx_data = {"location": {"areaDescription": "Unknown Location"}}

        reply = "{}: {} {}' {},{} {}h ago".format(
            searchcall,
            wx_data["location"]["areaDescription"],
            str(altfeet),
            str(lat),
            str(lon),
            str("%.1f" % round(delta_hours, 1)),
        ).rstrip()

        return reply
