import logging
import re

from aprsd import plugin, trace
import yfinance as yf

LOG = logging.getLogger("APRSD")


class StockPlugin(plugin.APRSDMessagePluginBase):
    """Stock market plugin for fetching stock quotes"""

    version = "1.0"
    command_regex = "^[sS]"
    command_name = "stock"

    @trace.trace
    def command(self, packet):
        LOG.info("StockPlugin")

        # fromcall = packet.get("from")
        message = packet.get("message_text", None)
        # ack = packet.get("msgNo", "0")

        a = re.search(r"^.*\s+(.*)", message)
        if a is not None:
            searchcall = a.group(1)
            stock_symbol = searchcall.upper()
        else:
            reply = "No stock symbol"
            return reply

        LOG.info("Fetch stock quote for '{}'".format(stock_symbol))

        try:
            stock = yf.Ticker(stock_symbol)
            reply = "{} - ask: {} high: {} low: {}".format(
                stock_symbol,
                stock.info["ask"],
                stock.info["dayHigh"],
                stock.info["dayLow"],
            )
        except Exception as e:
            LOG.error(
                "Failed to fetch stock '{}' from yahoo '{}'".format(stock_symbol, e),
            )
            reply = "Failed to fetch stock '{}'".format(stock_symbol)

        return reply.rstrip()
