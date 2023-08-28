import json
import logging

from oslo_config import cfg
import rpyc
from rpyc.utils.authenticators import AuthenticationError
from rpyc.utils.server import ThreadPoolServer

from aprsd import conf  # noqa: F401
from aprsd import packets, stats, threads
from aprsd.threads import log_monitor


CONF = cfg.CONF
LOG = logging.getLogger("APRSD")


def magic_word_authenticator(sock):
    client_ip = sock.getpeername()[0]
    magic = sock.recv(len(CONF.rpc_settings.magic_word)).decode()
    if magic != CONF.rpc_settings.magic_word:
        LOG.error(
            f"wrong magic word passed from {client_ip} "
            "'{magic}' != '{CONF.rpc_settings.magic_word}'",
        )
        raise AuthenticationError(
            f"wrong magic word passed in '{magic}'"
            f" != '{CONF.rpc_settings.magic_word}'",
        )
    return sock, None


class APRSDRPCThread(threads.APRSDThread):
    def __init__(self):
        super().__init__(name="RPCThread")
        self.thread = ThreadPoolServer(
            APRSDService,
            port=CONF.rpc_settings.port,
            protocol_config={"allow_public_attrs": True},
            authenticator=magic_word_authenticator,
        )

    def stop(self):
        if self.thread:
            self.thread.close()
        self.thread_stop = True

    def loop(self):
        # there is no loop as run is blocked
        if self.thread and not self.thread_stop:
            # This is a blocking call
            self.thread.start()


@rpyc.service
class APRSDService(rpyc.Service):
    def on_connect(self, conn):
        # code that runs when a connection is created
        # (to init the service, if needed)
        LOG.info("RPC Client Connected")
        self._conn = conn

    def on_disconnect(self, conn):
        # code that runs after the connection has already closed
        # (to finalize the service, if needed)
        LOG.info("RPC Client Disconnected")
        self._conn = None

    @rpyc.exposed
    def get_stats(self):
        stat = stats.APRSDStats()
        stats_dict = stat.stats()
        return_str = json.dumps(stats_dict, indent=4, sort_keys=True, default=str)
        return return_str

    @rpyc.exposed
    def get_stats_obj(self):
        return stats.APRSDStats()

    @rpyc.exposed
    def get_packet_list(self):
        return packets.PacketList()

    @rpyc.exposed
    def get_packet_track(self):
        return packets.PacketTrack()

    @rpyc.exposed
    def get_watch_list(self):
        return packets.WatchList()

    @rpyc.exposed
    def get_seen_list(self):
        return packets.SeenList()

    @rpyc.exposed
    def get_log_entries(self):
        entries = log_monitor.LogEntries().get_all_and_purge()
        return json.dumps(entries, default=str)
