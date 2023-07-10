import logging
import re
import time

from geopy.geocoders import Nominatim
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

        lat = float(aprs_data["entries"][0]["lat"])
        lon = float(aprs_data["entries"][0]["lng"])

        # Get some information about their location
        try:
            tic = time.perf_counter()
            geolocator = Nominatim(user_agent="APRSD")
            coordinates = f"{lat:0.6f}, {lon:0.6f}"
            location = geolocator.reverse(coordinates)
            address = location.raw.get("address")
            toc = time.perf_counter()
            if address:
                LOG.info(f"Geopy address {address} took {toc - tic:0.4f}")
            if address.get("country_code") == "us":
                area_info = f"{address.get('county')}, {address.get('state')}"
            else:
                # what to do for address for non US?
                area_info = f"{address.get('country'), 'Unknown'}"
        except Exception as ex:
            LOG.error(f"Failed to fetch Geopy address {ex}")
            area_info = "Unknown Location"

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

        reply = "{}: {} {}' {},{} {}h ago".format(
            searchcall,
            area_info,
            str(altfeet),
            f"{lat:0.2f}",
            f"{lon:0.2f}",
            str("%.1f" % round(delta_hours, 1)),
        ).rstrip()

        return reply
