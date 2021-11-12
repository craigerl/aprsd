import logging
import re
import time

from opencage.geocoder import OpenCageGeocode
import pytz

from aprsd import fuzzyclock, plugin, plugin_utils, trace


LOG = logging.getLogger("APRSD")


class TimePlugin(plugin.APRSDRegexCommandPluginBase):
    """Time command."""

    command_regex = "^[tT]"
    command_name = "time"
    short_description = "What is the current local time."

    def _get_local_tz(self):
        return pytz.timezone(time.strftime("%Z"))

    def _get_utcnow(self):
        return pytz.datetime.datetime.utcnow()

    def build_date_str(self, localzone):
        utcnow = self._get_utcnow()
        gmt_t = pytz.utc.localize(utcnow)
        local_t = gmt_t.astimezone(localzone)

        local_short_str = local_t.strftime("%H:%M %Z")
        local_hour = local_t.strftime("%H")
        local_min = local_t.strftime("%M")
        cur_time = fuzzyclock.fuzzy(int(local_hour), int(local_min), 1)

        reply = "{} ({})".format(
            cur_time,
            local_short_str,
        )

        return reply

    @trace.trace
    def process(self, packet):
        LOG.info("TIME COMMAND")
        # So we can mock this in unit tests
        localzone = self._get_local_tz()
        return self.build_date_str(localzone)


class TimeOpenCageDataPlugin(TimePlugin, plugin.APRSFIKEYMixin):
    """geocage based timezone fetching."""

    command_regex = "^[tT]"
    command_name = "time"
    short_description = "Current time of GPS beacon timezone. Uses OpenCage"

    def setup(self):
        self.ensure_aprs_fi_key()

    @trace.trace
    def process(self, packet):
        fromcall = packet.get("from")
        message = packet.get("message_text", None)
        # ack = packet.get("msgNo", "0")

        api_key = self.config["services"]["aprs.fi"]["apiKey"]

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
            LOG.error(f"Failed to fetch aprs.fi data {ex}")
            return "Failed to fetch location"

        # LOG.debug("LocationPlugin: aprs_data = {}".format(aprs_data))
        if not len(aprs_data["entries"]):
            LOG.error("Didn't get any entries from aprs.fi")
            return "Failed to fetch aprs.fi location"

        lat = aprs_data["entries"][0]["lat"]
        lon = aprs_data["entries"][0]["lng"]

        try:
            self.config.exists("opencagedata.apiKey")
        except Exception as ex:
            LOG.error(f"Failed to find config opencage:apiKey {ex}")
            return "No opencage apiKey found"

        try:
            opencage_key = self.config["opencagedata"]["apiKey"]
            geocoder = OpenCageGeocode(opencage_key)
            results = geocoder.reverse_geocode(lat, lon)
        except Exception as ex:
            LOG.error(f"Couldn't fetch opencagedata api '{ex}'")
            # Default to UTC instead
            localzone = pytz.timezone("UTC")
        else:
            tzone = results[0]["annotations"]["timezone"]["name"]
            localzone = pytz.timezone(tzone)

        return self.build_date_str(localzone)


class TimeOWMPlugin(TimePlugin, plugin.APRSFIKEYMixin):
    """OpenWeatherMap based timezone fetching."""

    command_regex = "^[tT]"
    command_name = "time"
    short_description = "Current time of GPS beacon's timezone. Uses OpenWeatherMap"

    def setup(self):
        self.ensure_aprs_fi_key()

    @trace.trace
    def process(self, packet):
        fromcall = packet.get("from")
        message = packet.get("message_text", None)
        # ack = packet.get("msgNo", "0")

        # optional second argument is a callsign to search
        a = re.search(r"^.*\s+(.*)", message)
        if a is not None:
            searchcall = a.group(1)
            searchcall = searchcall.upper()
        else:
            # if no second argument, search for calling station
            searchcall = fromcall

        api_key = self.config["services"]["aprs.fi"]["apiKey"]
        try:
            aprs_data = plugin_utils.get_aprs_fi(api_key, searchcall)
        except Exception as ex:
            LOG.error(f"Failed to fetch aprs.fi data {ex}")
            return "Failed to fetch location"

        LOG.debug(f"LocationPlugin: aprs_data = {aprs_data}")
        if not len(aprs_data["entries"]):
            LOG.error("Didn't get any entries from aprs.fi")
            return "Failed to fetch aprs.fi location"

        lat = aprs_data["entries"][0]["lat"]
        lon = aprs_data["entries"][0]["lng"]

        try:
            self.config.exists(
                ["services", "openweathermap", "apiKey"],
            )
        except Exception as ex:
            LOG.error(f"Failed to find config openweathermap:apiKey {ex}")
            return "No openweathermap apiKey found"

        api_key = self.config["services"]["openweathermap"]["apiKey"]
        try:
            results = plugin_utils.fetch_openweathermap(api_key, lat, lon)
        except Exception as ex:
            LOG.error(f"Couldn't fetch openweathermap api '{ex}'")
            # default to UTC
            localzone = pytz.timezone("UTC")
        else:
            tzone = results["timezone"]
            localzone = pytz.timezone(tzone)

        return self.build_date_str(localzone)
