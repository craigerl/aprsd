import json
import logging
import re

from oslo_config import cfg

from aprsd import packets, plugin, plugin_utils

CONF = cfg.CONF
LOG = logging.getLogger('APRSD')


class USWeatherPlugin(plugin.APRSDRegexCommandPluginBase, plugin.APRSFIKEYMixin):
    """USWeather Command

    Returns a weather report for the calling weather station
    inside the United States only.  This uses the
    forecast.weather.gov API to fetch the weather.

    This service does not require an apiKey.

    How to Call: Send a message to aprsd
    "weather" - returns weather near the calling callsign
    """

    command_regex = r'^[wW]'

    command_name = 'USWeather'
    short_description = 'Provide USA only weather of GPS Beacon location'

    def setup(self):
        self.ensure_aprs_fi_key()

    def process(self, packet: packets.MessagePacket) -> str:
        LOG.info('USWeatherPlugin')
        fromcall = packet.from_call
        message = packet.message_text
        a = re.search(r'^.*\s+(.*)', message)
        if a is not None:
            searchcall = a.group(1)
            searchcall = searchcall.upper()
        else:
            searchcall = fromcall
        api_key = CONF.aprs_fi.apiKey
        try:
            aprs_data = plugin_utils.get_aprs_fi(api_key, searchcall)
        except Exception as ex:
            LOG.error(f'Failed to fetch aprs.fi data {ex}')
            return 'Failed to fetch aprs.fi location'

        LOG.debug(f'LocationPlugin: aprs_data = {aprs_data}')
        if not len(aprs_data['entries']):
            LOG.error("Didn't get any entries from aprs.fi")
            return 'Failed to fetch aprs.fi location'

        lat = aprs_data['entries'][0]['lat']
        lon = aprs_data['entries'][0]['lng']

        try:
            wx_data = plugin_utils.get_weather_gov_for_gps(lat, lon)
        except Exception as ex:
            LOG.error(f"Couldn't fetch forecast.weather.gov '{ex}'")
            return 'Unable to get weather'

        LOG.debug(f'WX data {wx_data}')

        reply = (
            '%sF(%sF/%sF) %s. %s, %s.'
            % (
                wx_data['currentobservation']['Temp'],
                wx_data['data']['temperature'][0],
                wx_data['data']['temperature'][1],
                wx_data['data']['weather'][0],
                wx_data['time']['startPeriodName'][1],
                wx_data['data']['weather'][1],
            )
        ).rstrip()
        LOG.debug(f"reply: '{reply}' ")
        return reply


class USMetarPlugin(plugin.APRSDRegexCommandPluginBase, plugin.APRSFIKEYMixin):
    """METAR Command

    This provides a METAR weather report from a station near the caller
    or callsign using the forecast.weather.gov api.  This only works
    for stations inside the United States.

    This service does not require an apiKey.

    How to Call: Send a message to aprsd
    "metar" - returns metar report near the calling callsign
    "metar CALLSIGN" - returns metar report near CALLSIGN

    """

    command_regex = r'^([m]|[M]|[m]\s|metar)'
    command_name = 'USMetar'
    short_description = 'USA only METAR of GPS Beacon location'

    def setup(self):
        self.ensure_aprs_fi_key()

    def process(self, packet: packets.MessagePacket) -> str:
        LOG.info('USMetarPlugin')
        fromcall = packet.from_call
        message = packet.message_text
        a = re.search(r'^.*\s+(.*)', message)
        if a is not None:
            searchcall = a.group(1)
            station = searchcall.upper()
            try:
                resp = plugin_utils.get_weather_gov_metar(station)
            except Exception as e:
                LOG.debug(f'Weather failed with:  {str(e)}')
                reply = 'Unable to find station METAR'
            else:
                station_data = json.loads(resp.text)
                reply = station_data['properties']['rawMessage']

            return reply
        else:
            # if no second argument, search for calling station
            fromcall = fromcall

            api_key = CONF.aprs_fi.apiKey

            try:
                aprs_data = plugin_utils.get_aprs_fi(api_key, fromcall)
            except Exception as ex:
                LOG.error(f'Failed to fetch aprs.fi data {ex}')
                return 'Failed to fetch aprs.fi location'

            # LOG.debug("LocationPlugin: aprs_data = {}".format(aprs_data))
            if not len(aprs_data['entries']):
                LOG.error('Found no entries from aprs.fi!')
                return 'Failed to fetch aprs.fi location'

            lat = aprs_data['entries'][0]['lat']
            lon = aprs_data['entries'][0]['lng']

            try:
                wx_data = plugin_utils.get_weather_gov_for_gps(lat, lon)
            except Exception as ex:
                LOG.error(f"Couldn't fetch forecast.weather.gov '{ex}'")
                return 'Unable to metar find station.'

            if wx_data['location']['metar']:
                station = wx_data['location']['metar']
                try:
                    resp = plugin_utils.get_weather_gov_metar(station)
                except Exception as e:
                    LOG.debug(f'Weather failed with:  {str(e)}')
                    reply = 'Failed to get Metar'
                else:
                    station_data = json.loads(resp.text)
                    reply = station_data['properties']['rawMessage']
            else:
                # Couldn't find a station
                reply = 'No Metar station found'

        return reply
