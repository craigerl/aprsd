import logging
import re
import time

from geopy.geocoders import ArcGIS, AzureMaps, Baidu, Bing, GoogleV3
from geopy.geocoders import HereV7, Nominatim, OpenCage, TomTom, What3WordsV3, Woosmap
from oslo_config import cfg

from aprsd import packets, plugin, plugin_utils
from aprsd.utils import trace


CONF = cfg.CONF
LOG = logging.getLogger("APRSD")


class UsLocation:
    raw = {}

    def __init__(self, info):
        self.info = info

    def __str__(self):
        return self.info


class USGov:
    """US Government geocoder that uses the geopy API.

    This is a dummy class the implements the geopy reverse API,
    so the factory can return an object that conforms to the API.
    """
    def reverse(self, coordinates):
        """Reverse geocode a coordinate."""
        LOG.info(f"USGov reverse geocode {coordinates}")
        coords = coordinates.split(",")
        lat = float(coords[0])
        lon = float(coords[1])
        result = plugin_utils.get_weather_gov_for_gps(lat, lon)
        # LOG.info(f"WEATHER: {result}")
        # LOG.info(f"area description {result['location']['areaDescription']}")
        if 'location' in result:
            loc = UsLocation(result['location']['areaDescription'])
        else:
            loc = UsLocation("Unknown Location")

        LOG.info(f"USGov reverse geocode LOC {loc}")
        return loc


def geopy_factory():
    """Factory function for geopy geocoders."""
    geocoder = CONF.location_plugin.geopy_geocoder
    LOG.info(f"Using geocoder: {geocoder}")
    user_agent = CONF.location_plugin.user_agent
    LOG.info(f"Using user_agent: {user_agent}")

    if geocoder == "Nominatim":
        return Nominatim(user_agent=user_agent)
    elif geocoder == "USGov":
        return USGov()
    elif geocoder == "ArcGIS":
        return ArcGIS(
            username=CONF.location_plugin.arcgis_username,
            password=CONF.location_plugin.arcgis_password,
            user_agent=user_agent,
        )
    elif geocoder == "AzureMaps":
        return AzureMaps(
            user_agent=user_agent,
            subscription_key=CONF.location_plugin.azuremaps_subscription_key,
        )
    elif geocoder == "Baidu":
        return Baidu(user_agent=user_agent, api_key=CONF.location_plugin.baidu_api_key)
    elif geocoder == "Bing":
        return Bing(user_agent=user_agent, api_key=CONF.location_plugin.bing_api_key)
    elif geocoder == "GoogleV3":
        return GoogleV3(user_agent=user_agent, api_key=CONF.location_plugin.google_api_key)
    elif geocoder == "HERE":
        return HereV7(user_agent=user_agent, api_key=CONF.location_plugin.here_api_key)
    elif geocoder == "OpenCage":
        return OpenCage(user_agent=user_agent, api_key=CONF.location_plugin.opencage_api_key)
    elif geocoder == "TomTom":
        return TomTom(user_agent=user_agent, api_key=CONF.location_plugin.tomtom_api_key)
    elif geocoder == "What3Words":
        return What3WordsV3(user_agent=user_agent, api_key=CONF.location_plugin.what3words_api_key)
    elif geocoder == "Woosmap":
        return Woosmap(user_agent=user_agent, api_key=CONF.location_plugin.woosmap_api_key)
    else:
        raise ValueError(f"Unknown geocoder: {geocoder}")


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
            geolocator = geopy_factory()
            LOG.info(f"Using GEOLOCATOR: {geolocator}")
            coordinates = f"{lat:0.6f}, {lon:0.6f}"
            location = geolocator.reverse(coordinates)
            address = location.raw.get("address")
            LOG.debug(f"GEOLOCATOR address: {address}")
            toc = time.perf_counter()
            if address:
                LOG.info(f"Geopy address {address} took {toc - tic:0.4f}")
                if address.get("country_code") == "us":
                    area_info = f"{address.get('county')}, {address.get('state')}"
                else:
                    # what to do for address for non US?
                    area_info = f"{address.get('country'), 'Unknown'}"
            else:
                area_info = str(location)
        except Exception as ex:
            LOG.error(ex)
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
