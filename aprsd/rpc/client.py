import json
import logging

from oslo_config import cfg
import rpyc

from aprsd import conf  # noqa
from aprsd import rpc


CONF = cfg.CONF
LOG = logging.getLogger("APRSD")


class RPCClient:
    _instance = None
    _rpc_client = None

    ip = None
    port = None
    magic_word = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, ip=None, port=None, magic_word=None):
        if ip:
            self.ip = ip
        else:
            self.ip = CONF.rpc_settings.ip
        if port:
            self.port = int(port)
        else:
            self.port = CONF.rpc_settings.port
        if magic_word:
            self.magic_word = magic_word
        else:
            self.magic_word = CONF.rpc_settings.magic_word
        self._check_settings()
        self.get_rpc_client()

    def _check_settings(self):
        if not CONF.rpc_settings.enabled:
            LOG.warning("RPC is not enabled, no way to get stats!!")

        if self.magic_word == conf.common.APRSD_DEFAULT_MAGIC_WORD:
            LOG.warning("You are using the default RPC magic word!!!")
            LOG.warning("edit aprsd.conf and change rpc_settings.magic_word")

        LOG.debug(f"RPC Client: {self.ip}:{self.port} {self.magic_word}")

    def _rpyc_connect(
            self, host, port, service=rpyc.VoidService,
            config={}, ipv6=False,
            keepalive=False, authorizer=None, ):

        LOG.info(f"Connecting to RPC host '{host}:{port}'")
        try:
            s = rpc.AuthSocketStream.connect(
                host, port, ipv6=ipv6, keepalive=keepalive,
                authorizer=authorizer,
            )
            return rpyc.utils.factory.connect_stream(s, service, config=config)
        except ConnectionRefusedError:
            LOG.error(f"Failed to connect to RPC host '{host}:{port}'")
            return None

    def get_rpc_client(self):
        if not self._rpc_client:
            self._rpc_client = self._rpyc_connect(
                self.ip,
                self.port,
                authorizer=lambda sock: sock.send(self.magic_word.encode()),
            )
        return self._rpc_client

    def get_stats_dict(self):
        cl = self.get_rpc_client()
        result = {}
        if not cl:
            return result

        try:
            rpc_stats_dict = cl.root.get_stats()
            result = json.loads(rpc_stats_dict)
        except EOFError:
            LOG.error("Lost connection to RPC Host")
            self._rpc_client = None
        return result

    def get_stats(self):
        cl = self.get_rpc_client()
        result = {}
        if not cl:
            return result

        try:
            result = cl.root.get_stats_obj()
        except EOFError:
            LOG.error("Lost connection to RPC Host")
            self._rpc_client = None
        return result

    def get_packet_track(self):
        cl = self.get_rpc_client()
        result = None
        if not cl:
            return result
        try:
            result = cl.root.get_packet_track()
        except EOFError:
            LOG.error("Lost connection to RPC Host")
            self._rpc_client = None
        return result

    def get_packet_list(self):
        cl = self.get_rpc_client()
        result = None
        if not cl:
            return result
        try:
            result = cl.root.get_packet_list()
        except EOFError:
            LOG.error("Lost connection to RPC Host")
            self._rpc_client = None
        return result

    def get_watch_list(self):
        cl = self.get_rpc_client()
        result = None
        if not cl:
            return result
        try:
            result = cl.root.get_watch_list()
        except EOFError:
            LOG.error("Lost connection to RPC Host")
            self._rpc_client = None
        return result

    def get_seen_list(self):
        cl = self.get_rpc_client()
        result = None
        if not cl:
            return result
        try:
            result = cl.root.get_seen_list()
        except EOFError:
            LOG.error("Lost connection to RPC Host")
            self._rpc_client = None
        return result

    def get_log_entries(self):
        cl = self.get_rpc_client()
        result = None
        if not cl:
            return result
        try:
            result_str = cl.root.get_log_entries()
            result = json.loads(result_str)
        except EOFError:
            LOG.error("Lost connection to RPC Host")
            self._rpc_client = None
        return result
