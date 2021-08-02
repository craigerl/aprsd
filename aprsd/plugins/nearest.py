import logging

from aprsd import plugin, plugin_utils, trace, utils
import requests

LOG = logging.getLogger("APRSD")


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
        if len(command_parts) == 3:
            # Must be in
            count = command_parts[1]
            band = command_parts[2]
        elif len(command_parts) == 2:
            if "m" in command_parts[1]:
                band = command_parts[1]
                count = 1
            else:
                count = command_parts[1]
                band = "2m"
        else:
            count = 1
            band = "2m"

        LOG.info("Looking for {} nearest stations in band {}".format(count, band))

        try:
            url = "http://0.0.0.0:8081/nearest"
            parameters = {"lat": lat, "lon": lon, "count": count, "band": band}
            result = requests.post(url=url, params=parameters)
            data = result.json()
            LOG.info(data)
        except Exception as ex:
            LOG.error("Couldn't fetch nearest stations '{}'".format(ex))
            data = None

        if data:
            # just do the first one for now
            replies = []
            for entry in data:
                LOG.info("Using {}".format(entry))
                reply = "{} {} PL{}  {}m  {}".format(
                    entry["callsign"],
                    entry["frequency"],
                    entry["offset"],
                    entry["distance"],
                    entry["direction"],
                )
                replies.append(reply)

            return replies
        else:
            return "Failed"
