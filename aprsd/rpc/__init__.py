import rpyc


class AuthSocketStream(rpyc.SocketStream):
    """Used to authenitcate the RPC stream to remote."""

    @classmethod
    def connect(cls, *args, authorizer=None, **kwargs):
        stream_obj = super().connect(*args, **kwargs)

        if callable(authorizer):
            authorizer(stream_obj.sock)

        return stream_obj
