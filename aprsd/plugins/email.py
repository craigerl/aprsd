import logging
import re
import time

from aprsd import email, messaging, plugin, trace

LOG = logging.getLogger("APRSD")


class EmailPlugin(plugin.APRSDMessagePluginBase):
    """Email Plugin."""

    version = "1.0"
    command_regex = "^-.*"
    command_name = "email"

    # message_number:time combos so we don't resend the same email in
    # five mins {int:int}
    email_sent_dict = {}

    @trace.trace
    def command(self, packet):
        LOG.info("Email COMMAND")

        fromcall = packet.get("from")
        message = packet.get("message_text", None)
        ack = packet.get("msgNo", "0")

        reply = None
        if not self.config["aprsd"]["email"].get("enabled", False):
            LOG.debug("Email is not enabled in config file ignoring.")
            return "Email not enabled."

        searchstring = "^" + self.config["ham"]["callsign"] + ".*"
        # only I can do email
        if re.search(searchstring, fromcall):
            # digits only, first one is number of emails to resend
            r = re.search("^-([0-9])[0-9]*$", message)
            if r is not None:
                LOG.debug("RESEND EMAIL")
                email.resend_email(r.group(1), fromcall)
                reply = messaging.NULL_MESSAGE
            # -user@address.com body of email
            elif re.search(r"^-([A-Za-z0-9_\-\.@]+) (.*)", message):
                # (same search again)
                a = re.search(r"^-([A-Za-z0-9_\-\.@]+) (.*)", message)
                if a is not None:
                    to_addr = a.group(1)
                    content = a.group(2)

                    email_address = email.get_email_from_shortcut(to_addr)
                    if not email_address:
                        reply = "Bad email address"
                        return reply

                    # send recipient link to aprs.fi map
                    if content == "mapme":
                        content = "Click for my location: http://aprs.fi/{}".format(
                            self.config["ham"]["callsign"],
                        )
                    too_soon = 0
                    now = time.time()
                    # see if we sent this msg number recently
                    if ack in self.email_sent_dict:
                        # BUG(hemna) - when we get a 2 different email command
                        # with the same ack #, we don't send it.
                        timedelta = now - self.email_sent_dict[ack]
                        if timedelta < 300:  # five minutes
                            too_soon = 1
                    if not too_soon or ack == 0:
                        LOG.info("Send email '{}'".format(content))
                        send_result = email.send_email(to_addr, content)
                        reply = messaging.NULL_MESSAGE
                        if send_result != 0:
                            reply = "-{} failed".format(to_addr)
                            # messaging.send_message(fromcall, "-" + to_addr + " failed")
                        else:
                            # clear email sent dictionary if somehow goes over 100
                            if len(self.email_sent_dict) > 98:
                                LOG.debug(
                                    "DEBUG: email_sent_dict is big ("
                                    + str(len(self.email_sent_dict))
                                    + ") clearing out.",
                                )
                                self.email_sent_dict.clear()
                            self.email_sent_dict[ack] = now
                    else:
                        reply = messaging.NULL_MESSAGE
                        LOG.info(
                            "Email for message number "
                            + ack
                            + " recently sent, not sending again.",
                        )
            else:
                reply = "Bad email address"
                # messaging.send_message(fromcall, "Bad email address")

        return reply
