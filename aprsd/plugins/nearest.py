import logging

from aprsd import plugin, plugin_utils, trace, utils
import requests

LOG = logging.getLogger("APRSD")

API_KEY_HEADER = "X-Api-Key"

# Copied over from haminfo.utils
# create from
# http://www.arrl.org/band-plan
FREQ_BAND_PLAN = {
    "160m": {"desc": "160 Meters (1.8-2.0 MHz)", "low": 1.8, "high": 2.0},
    "80m": {"desc": "80 Meters (3.5-4.0 MHz)", "low": 3.5, "high": 4.0},
    "60m": {"desc": "60 Meters (5 MHz channels)", "low": 5.0, "high": 5.9},
    "40m": {"desc": "40 Meters (7.0 - 7.3 MHz)", "low": 7.0, "high": 7.3},
    "30m": {"desc": "30 Meters(10.1 - 10.15 MHz)", "low": 10.1, "high": 10.15},
    "20m": {"desc": "20 Meters(14.0 - 14.35 MHz)", "low": 14.0, "high": 14.35},
    "17m": {
        "desc": "17 Meters(18.068 - 18.168 MHz)",
        "low": 18.068,
        "high": 18.168,
    },
    "15m": {"desc": "15 Meters(21.0 - 21.45 MHz)", "low": 21.0, "high": 21.45},
    "12m": {
        "desc": "12 Meters(24.89 - 24.99 MHz)",
        "low": 24.89,
        "high": 24.99,
    },
    "10m": {"desc": "10 Meters(28 - 29.7 MHz)", "low": 28.0, "high": 29.7},
    "6m": {"desc": "6 Meters(50 - 54 MHz)", "low": 50.0, "high": 54.0},
    "2m": {"desc": "2 Meters(144 - 148 MHz)", "low": 144.0, "high": 148.0},
    "1.25m": {
        "desc": "1.25 Meters(222 - 225 MHz)",
        "low": 222.0,
        "high": 225.0,
    },
    "70cm": {
        "desc": "70 Centimeters(420 - 450 MHz)",
        "low": 420.0,
        "high": 450,
    },
    "33cm": {
        "desc": "33 Centimeters(902 - 928 MHz)",
        "low": 902.0,
        "high": 928,
    },
    "23cm": {
        "desc": "23 Centimeters(1240 - 1300 MHz)",
        "low": 1240.0,
        "high": 1300.0,
    },
    "13cm": {
        "desc": "13 Centimeters(2300 - 2310 and 2390 - 2450 MHz)",
        "low": 2300.0,
        "high": 2450.0,
    },
    "9cm": {
        "desc": "9 centimeters(3300-3500 MHz)",
        "low": 3300.0,
        "high": 3500.0,
    },
    "5cm": {
        "desc": "5 Centimeters(5650.0 - 5925.0 MHz)",
        "low": 5650.0,
        "high": 5290.0,
    },
    "3cm": {
        "desc": "3 Centimeters(10000.000 - 10500.000 MHz )",
        "low": 10000.0,
        "high": 10500.0,
    },
}

# Mapping of human filter string to db column name
# These are the allowable filters.
STATION_FEATURES = {
    "ares": "ares",
    "races": "races",
    "skywarn": "skywarn",
    "allstar": "allstar_node",
    "echolink": "echolink_node",
    "irlp": "irlp_node",
    "wires": "wires_node",
    "fm": "fm_analog",
    "dmr": "dmr",
    "dstar": "dstar",
}


class NearestPlugin(plugin.APRSDMessagePluginBase):
    """Nearest!

    Syntax of request

    n[earest] [count] [band]

    count - the number of stations to return
    band  - the frequency band to look for
            Defaults to 2m


    """

    version = "1.0"
    command_regex = "^[nN]"
    command_name = "nearest"

    @trace.trace
    def command(self, packet):
        LOG.info("Nearest Plugin")
        fromcall = packet.get("from")
        message = packet.get("message_text", None)
        # ack = packet.get("msgNo", "0")

        # get last location of a callsign, get descriptive name from weather service
        try:
            utils.check_config_option(self.config, ["services", "aprs.fi", "apiKey"])
        except Exception as ex:
            LOG.error("Failed to find config aprs.fi:apikey {}".format(ex))
            return "No aprs.fi apikey found"

        api_key = self.config["services"]["aprs.fi"]["apiKey"]

        try:
            aprs_data = plugin_utils.get_aprs_fi(api_key, fromcall)
        except Exception as ex:
            LOG.error("Failed to fetch aprs.fi '{}'".format(ex))
            return "Failed to fetch aprs.fi location"

        LOG.debug("NearestPlugin: aprs_data = {}".format(aprs_data))
        if not len(aprs_data["entries"]):
            LOG.error("Didn't get any entries from aprs.fi")
            return "Failed to fetch aprs.fi location"

        lat = aprs_data["entries"][0]["lat"]
        lon = aprs_data["entries"][0]["lng"]

        command_parts = message.split(" ")
        # try and decipher the request parameters
        # n[earest] should be part[0]
        # part[1] could be

        def isInt(value):
            try:
                int(value)
                return True
            except ValueError:
                return False

        # The command reference is:
        # N[earest] [<fields>]
        # IF it's a number, it's the number stations to return
        # if it has an '<int>m' in it, that's the frequency band
        # if it starts with a +<key> it's a filter.
        count = None
        band = None
        filters = []
        for part in command_parts[1:]:
            LOG.debug(part)
            if isInt(part):
                # this is the number of stations
                count = int(part)
            elif part.endswith("m"):
                # this is the frequency band
                if part in FREQ_BAND_PLAN:
                    band = part
                else:
                    LOG.error(
                        "User tried to use an invalid frequency band {}".format(part),
                    )
            elif part.startswith("+"):
                # this is the filtering
                if part[1:] in STATION_FEATURES:
                    filters.append(part[1:])

        if not count:
            # They didn't specify a count
            # so we default to 1
            count = 1

        if not band:
            # They didn't specify a frequency band
            # so we use 2meters
            band = "2m"

        LOG.info(
            "Looking for {} nearest stations in band {} "
            "with filters: {}".format(count, band, filters),
        )

        try:
            url = "{}/nearest".format(
                self.config["services"]["haminfo"]["base_url"],
            )
            api_key = self.config["services"]["haminfo"]["apiKey"]
            params = {"lat": lat, "lon": lon, "count": count, "band": band}
            if filters:
                params["filters"] = ",".join(filters)

            headers = {API_KEY_HEADER: api_key}
            result = requests.post(url=url, json=params, headers=headers)
            data = result.json()
            # LOG.info(data)
        except Exception as ex:
            LOG.error("Couldn't fetch nearest stations '{}'".format(ex))
            data = None

        def isfloat(value):
            try:
                float(value)
                return True
            except ValueError:
                return False

        if data:
            # just do the first one for now
            replies = []
            for entry in data:
                LOG.info("Using {}".format(entry))

                if isfloat(entry["offset"]) and float(entry["offset"]) > 0:
                    offset_direction = "+"
                else:
                    offset_direction = "-"

                if isfloat(entry["distance"]):
                    distance = round(float(entry["distance"]))
                else:
                    distance = entry["distance"]

                reply = "{} {}{} T{} {}mi {}".format(
                    entry["callsign"],
                    entry["frequency"],
                    offset_direction,
                    entry["uplink_offset"],
                    distance,
                    entry["direction"],
                )
                replies.append(reply)
            return replies
        else:
            return "Failed"
