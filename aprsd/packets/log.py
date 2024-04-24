import logging
from typing import Optional

from loguru import logger
from oslo_config import cfg

from aprsd.packets.core import AckPacket, RejectPacket


LOG = logging.getLogger()
LOGU = logger
CONF = cfg.CONF

FROM_COLOR = "fg #C70039"
TO_COLOR = "fg #D033FF"
TX_COLOR = "red"
RX_COLOR = "green"
PACKET_COLOR = "cyan"


def log_multiline(packet, tx: Optional[bool] = False, header: Optional[bool] = True) -> None:
    """LOG a packet to the logfile."""
    if not CONF.enable_packet_logging:
        return
    if CONF.log_packet_format == "compact":
        return

    # asdict(packet)
    logit = ["\n"]
    name = packet.__class__.__name__

    if isinstance(packet, AckPacket):
        pkt_max_send_count = CONF.default_ack_send_count
    else:
        pkt_max_send_count = CONF.default_packet_send_count

    if header:
        if tx:
            header_str = f"<{TX_COLOR}>TX</{TX_COLOR}>"
            logit.append(
                f"{header_str}________(<{PACKET_COLOR}>{name}</{PACKET_COLOR}>  "
                f"TX:{packet.send_count + 1} of {pkt_max_send_count}",
            )
        else:
            header_str = f"<{RX_COLOR}>RX</{RX_COLOR}>"
            logit.append(
                f"{header_str}________(<{PACKET_COLOR}>{name}</{PACKET_COLOR}>)",
            )

    else:
        header_str = ""
        logit.append(f"__________(<{PACKET_COLOR}>{name}</{PACKET_COLOR}>)")
    # log_list.append(f"  Packet  : {packet.__class__.__name__}")
    if packet.msgNo:
        logit.append(f"  Msg #   : {packet.msgNo}")
    if packet.from_call:
        logit.append(f"  From    : <{FROM_COLOR}>{packet.from_call}</{FROM_COLOR}>")
    if packet.to_call:
        logit.append(f"  To      : <{TO_COLOR}>{packet.to_call}</{TO_COLOR}>")
    if hasattr(packet, "path") and packet.path:
        logit.append(f"  Path    : {'=>'.join(packet.path)}")
    if hasattr(packet, "via") and packet.via:
        logit.append(f"  VIA     : {packet.via}")

    if not isinstance(packet, AckPacket) and not isinstance(packet, RejectPacket):
        msg = packet.human_info

        if msg:
            msg = msg.replace("<", "\\<")
            logit.append(f"  Info    : <light-yellow><b>{msg}</b></light-yellow>")

    if hasattr(packet, "comment") and packet.comment:
        logit.append(f"  Comment : {packet.comment}")

    raw = packet.raw.replace("<", "\\<")
    logit.append(f"  Raw     : <fg #828282>{raw}</fg #828282>")
    logit.append(f"{header_str}________(<{PACKET_COLOR}>{name}</{PACKET_COLOR}>)")

    LOGU.opt(colors=True).info("\n".join(logit))
    LOG.debug(repr(packet))


def log(packet, tx: Optional[bool] = False, header: Optional[bool] = True) -> None:
    if not CONF.enable_packet_logging:
        return
    if CONF.log_packet_format == "multiline":
        log_multiline(packet, tx, header)
        return

    logit = []
    name = packet.__class__.__name__
    if isinstance(packet, AckPacket):
        pkt_max_send_count = CONF.default_ack_send_count
    else:
        pkt_max_send_count = CONF.default_packet_send_count

    if header:
        if tx:
            via_color = "red"
            arrow = f"<{via_color}>-></{via_color}>"
            logit.append(
                f"<red>TX {arrow}</red> "
                f"<cyan>{name}</cyan>"
                f":{packet.msgNo}"
                f" ({packet.send_count + 1} of {pkt_max_send_count})",
            )
        else:
            via_color = "fg #828282"
            arrow = f"<{via_color}>-></{via_color}>"
            left_arrow = f"<{via_color}><-</{via_color}>"
            logit.append(
                f"<fg #1AA730>RX</fg #1AA730> {left_arrow} "
                f"<cyan>{name}</cyan>"
                f":{packet.msgNo}",
            )
    else:
        via_color = "green"
        arrow = f"<{via_color}>-></{via_color}>"
        logit.append(
            f"<cyan>{name}</cyan>"
            f":{packet.msgNo}",
        )

    tmp = None
    if packet.path:
        tmp = f"{arrow}".join(packet.path) + f"{arrow} "

    logit.append(
        f"<{FROM_COLOR}>{packet.from_call}</{FROM_COLOR}> {arrow}"
        f"{tmp if tmp else ' '}"
        f"<{TO_COLOR}>{packet.to_call}</{TO_COLOR}>",
    )

    if not isinstance(packet, AckPacket) and not isinstance(packet, RejectPacket):
        logit.append(":")
        msg = packet.human_info

        if msg:
            msg = msg.replace("<", "\\<")
            logit.append(f"<light-yellow><b>{msg}</b></light-yellow>")

    LOGU.opt(colors=True).info(" ".join(logit))
    log_multiline(packet, tx, header)
