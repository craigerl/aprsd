import logging
import re

import yfinance as yf

from aprsd import plugin, trace


LOG = logging.getLogger("APRSD")


class StockPlugin(plugin.APRSDRegexCommandPluginBase):
    """Stock market plugin for fetching stock quotes"""

    version = "1.0"
    command_regex = "^[sS]"
    command_name = "stock"

    @trace.trace
    def process(self, packet):
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

        LOG.info(f"Fetch stock quote for '{stock_symbol}'")

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
                f"Failed to fetch stock '{stock_symbol}' from yahoo '{e}'",
            )
            reply = f"Failed to fetch stock '{stock_symbol}'"

        return reply.rstrip()
