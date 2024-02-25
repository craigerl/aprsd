import logging
import select
import threading

import aprslib
from aprslib import is_py3
from aprslib.exceptions import (
    ConnectionDrop, ConnectionError, GenericError, LoginError, ParseError,
    UnknownFormat,
)
import wrapt

import aprsd
from aprsd import stats
from aprsd.packets import core


LOG = logging.getLogger("APRSD")


class Aprsdis(aprslib.IS):
    """Extend the aprslib class so we can exit properly."""

    # flag to tell us to stop
    thread_stop = False

    # timeout in seconds
    select_timeout = 1
    lock = threading.Lock()

    def stop(self):
        self.thread_stop = True
        LOG.info("Shutdown Aprsdis client.")

    @wrapt.synchronized(lock)
    def send(self, packet: core.Packet):
        """Send an APRS Message object."""
        self.sendall(packet.raw)

    def is_alive(self):
        """If the connection is alive or not."""
        return self._connected

    def _socket_readlines(self, blocking=False):
        """
        Generator for complete lines, received from the server
        """
        try:
            self.sock.setblocking(0)
        except OSError as e:
            self.logger.error(f"socket error when setblocking(0): {str(e)}")
            raise aprslib.ConnectionDrop("connection dropped")

        while not self.thread_stop:
            short_buf = b""
            newline = b"\r\n"

            # set a select timeout, so we get a chance to exit
            # when user hits CTRL-C
            readable, writable, exceptional = select.select(
                [self.sock],
                [],
                [],
                self.select_timeout,
            )
            if not readable:
                if not blocking:
                    break
                else:
                    continue

            try:
                short_buf = self.sock.recv(4096)

                # sock.recv returns empty if the connection drops
                if not short_buf:
                    if not blocking:
                        # We could just not be blocking, so empty is expected
                        continue
                    else:
                        self.logger.error("socket.recv(): returned empty")
                        raise aprslib.ConnectionDrop("connection dropped")
            except OSError as e:
                # self.logger.error("socket error on recv(): %s" % str(e))
                if "Resource temporarily unavailable" in str(e):
                    if not blocking:
                        if len(self.buf) == 0:
                            break

            self.buf += short_buf

            while newline in self.buf:
                line, self.buf = self.buf.split(newline, 1)

                yield line

    def _send_login(self):
        """
        Sends login string to server
        """
        login_str = "user {0} pass {1} vers github.com/craigerl/aprsd {3}{2}\r\n"
        login_str = login_str.format(
            self.callsign,
            self.passwd,
            (" filter " + self.filter) if self.filter != "" else "",
            aprsd.__version__,
        )

        self.logger.debug("Sending login information")

        try:
            self._sendall(login_str)
            self.sock.settimeout(5)
            test = self.sock.recv(len(login_str) + 100)
            if is_py3:
                test = test.decode("latin-1")
            test = test.rstrip()

            self.logger.debug("Server: '%s'", test)

            if not test:
                raise LoginError(f"Server Response Empty: '{test}'")

            _, _, callsign, status, e = test.split(" ", 4)
            s = e.split(",")
            if len(s):
                server_string = s[0].replace("server ", "")
            else:
                server_string = e.replace("server ", "")

            if callsign == "":
                raise LoginError("Server responded with empty callsign???")
            if callsign != self.callsign:
                raise LoginError(f"Server: {test}")
            if status != "verified," and self.passwd != "-1":
                raise LoginError("Password is incorrect")

            if self.passwd == "-1":
                self.logger.info("Login successful (receive only)")
            else:
                self.logger.info("Login successful")

            self.logger.info(f"Connected to {server_string}")
            self.server_string = server_string
            stats.APRSDStats().set_aprsis_server(server_string)

        except LoginError as e:
            self.logger.error(str(e))
            self.close()
            raise
        except Exception as e:
            self.close()
            self.logger.error(f"Failed to login '{e}'")
            self.logger.exception(e)
            raise LoginError("Failed to login")

    def consumer(self, callback, blocking=True, immortal=False, raw=False):
        """
        When a position sentence is received, it will be passed to the callback function

        blocking: if true (default), runs forever, otherwise will return after one sentence
                  You can still exit the loop, by raising StopIteration in the callback function

        immortal: When true, consumer will try to reconnect and stop propagation of Parse exceptions
                  if false (default), consumer will return

        raw: when true, raw packet is passed to callback, otherwise the result from aprs.parse()
        """

        if not self._connected:
            raise ConnectionError("not connected to a server")

        line = b""

        while True and not self.thread_stop:
            try:
                for line in self._socket_readlines(blocking):
                    if line[0:1] != b"#":
                        if raw:
                            callback(line)
                        else:
                            callback(self._parse(line))
                    else:
                        self.logger.debug("Server: %s", line.decode("utf8"))
                        stats.APRSDStats().set_aprsis_keepalive()
            except ParseError as exp:
                self.logger.log(
                    11,
                    "%s\n    Packet: %s",
                    exp,
                    exp.packet,
                )
            except UnknownFormat as exp:
                self.logger.log(
                    9,
                    "%s\n    Packet: %s",
                    exp,
                    exp.packet,
                )
            except LoginError as exp:
                self.logger.error("%s: %s", exp.__class__.__name__, exp)
            except (KeyboardInterrupt, SystemExit):
                raise
            except (ConnectionDrop, ConnectionError):
                self.close()

                if not immortal:
                    raise
                else:
                    self.connect(blocking=blocking)
                    continue
            except GenericError:
                pass
            except StopIteration:
                break
            except Exception:
                self.logger.error("APRS Packet: %s", line)
                raise

            if not blocking:
                break
