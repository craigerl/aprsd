import datetime
import logging
import select
import socket
import threading

import aprslib
import wrapt
from aprslib import is_py3
from aprslib.exceptions import (
    ConnectionDrop,
    ConnectionError,
    GenericError,
    LoginError,
    ParseError,
    UnknownFormat,
)

import aprsd
from aprsd.packets import core

LOG = logging.getLogger('APRSD')


class Aprsdis(aprslib.IS):
    """Extend the aprslib class so we can exit properly."""

    # flag to tell us to stop
    thread_stop = False

    # date for last time we heard from the server
    aprsd_keepalive = datetime.datetime.now()

    # Which server we are connected to?
    server_string = 'None'

    # timeout in seconds
    select_timeout = 1
    lock = threading.Lock()

    def stop(self):
        self.thread_stop = True
        LOG.warning('Shutdown Aprsdis client.')

    def close(self):
        LOG.warning('Closing Aprsdis client.')
        super().close()

    @wrapt.synchronized(lock)
    def send(self, packet: core.Packet):
        """Send an APRS Message object."""
        self.sendall(packet.raw)

    def is_alive(self):
        """If the connection is alive or not."""
        return self._connected

    def _connect(self):
        """
        Attemps connection to the server
        """

        self.logger.info(
            'Attempting connection to %s:%s', self.server[0], self.server[1]
        )

        try:
            self._open_socket()

            peer = self.sock.getpeername()

            self.logger.info('Connected to %s', str(peer))

            # 5 second timeout to receive server banner
            self.sock.setblocking(1)
            self.sock.settimeout(5)

            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            # MACOS doesn't have TCP_KEEPIDLE
            if hasattr(socket, 'TCP_KEEPIDLE'):
                self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 1)
            self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 3)
            self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 5)

            banner = self.sock.recv(512)
            if is_py3:
                banner = banner.decode('latin-1')

            if banner[0] == '#':
                self.logger.debug('Banner: %s', banner.rstrip())
            else:
                raise ConnectionError('invalid banner from server')

        except ConnectionError as e:
            self.logger.error(str(e))
            self.close()
            raise
        except (socket.error, socket.timeout) as e:
            self.close()

            self.logger.error('Socket error: %s' % str(e))
            if str(e) == 'timed out':
                raise ConnectionError('no banner from server') from e
            else:
                raise ConnectionError(e) from e

        self._connected = True

    def _socket_readlines(self, blocking=False):
        """
        Generator for complete lines, received from the server
        """
        try:
            self.sock.setblocking(0)
        except OSError as e:
            self.logger.error(f'socket error when setblocking(0): {str(e)}')
            raise aprslib.ConnectionDrop('connection dropped') from e

        while not self.thread_stop:
            short_buf = b''
            newline = b'\r\n'

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
                        self.logger.error('socket.recv(): returned empty')
                        raise aprslib.ConnectionDrop('connection dropped')
            except OSError as e:
                # self.logger.error("socket error on recv(): %s" % str(e))
                if 'Resource temporarily unavailable' in str(e):
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
        login_str = 'user {0} pass {1} vers Python-APRSD {3}{2}\r\n'
        login_str = login_str.format(
            self.callsign,
            self.passwd,
            (' filter ' + self.filter) if self.filter != '' else '',
            aprsd.__version__,
        )

        self.logger.debug('Sending login information')

        try:
            self._sendall(login_str)
            self.sock.settimeout(5)
            test = self.sock.recv(len(login_str) + 100)
            if is_py3:
                test = test.decode('latin-1')
            test = test.rstrip()

            self.logger.debug("Server: '%s'", test)

            if not test:
                raise LoginError(f"Server Response Empty: '{test}'")

            _, _, callsign, status, e = test.split(' ', 4)
            s = e.split(',')
            if len(s):
                server_string = s[0].replace('server ', '')
            else:
                server_string = e.replace('server ', '')

            if callsign == '':
                raise LoginError('Server responded with empty callsign???')
            if callsign != self.callsign:
                raise LoginError(f'Server: {test}')
            if status != 'verified,' and self.passwd != '-1':
                raise LoginError('Password is incorrect')

            if self.passwd == '-1':
                self.logger.info('Login successful (receive only)')
            else:
                self.logger.info('Login successful')

            self.logger.info(f'Connected to {server_string}')
            self.server_string = server_string

        except LoginError as e:
            self.logger.error(str(e))
            self.close()
            raise
        except Exception as e:
            self.close()
            self.logger.error(f"Failed to login '{e}'")
            self.logger.exception(e)
            raise LoginError('Failed to login') from e

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
            raise ConnectionError('not connected to a server')

        line = b''

        while True and not self.thread_stop:
            try:
                for line in self._socket_readlines(blocking):
                    if line[0:1] != b'#':
                        self.aprsd_keepalive = datetime.datetime.now()
                        if raw:
                            callback(line)
                        else:
                            callback(self._parse(line))
                    else:
                        self.logger.debug('Server: %s', line.decode('utf8'))
                        self.aprsd_keepalive = datetime.datetime.now()
            except ParseError as exp:
                self.logger.log(
                    11,
                    "%s    Packet: '%s'",
                    exp,
                    exp.packet,
                )
            except UnknownFormat as exp:
                self.logger.log(
                    9,
                    "%s    Packet: '%s'",
                    exp,
                    exp.packet,
                )
            except LoginError as exp:
                self.logger.error('%s: %s', exp.__class__.__name__, exp)
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
                self.logger.error('APRS Packet: %s', line)
                raise

            if not blocking:
                break
