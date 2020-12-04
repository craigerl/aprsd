#!/bin/python

import argparse
import logging
import os
import select
import signal
import socket
import sys
import time
import threading
import Queue

from logging.handlers import RotatingFileHandler
from telnetsrv.green import TelnetHandler, command

from aprsd import utils

# command line args
parser = argparse.ArgumentParser()
parser.add_argument("--loglevel",
                    default='DEBUG',
                    choices=['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG'],
                    help="The log level to use for aprsd.log")
parser.add_argument("--quiet",
                    action='store_true',
                    help="Don't log to stdout")

parser.add_argument("--port",
                    default=9099,
                    type=int,
                    help="The port to listen on .")
parser.add_argument("--ip",
                    default='127.0.0.1',
                    help="The IP to listen on ")

args = parser.parse_args()

CONFIG = None
LOG = logging.getLogger('ARPSSERVER')


class MyAPRSServer(TelnetHandler):

    @command('echo')
    def command_echo(self, params):
        LOG.debug("ECHO %s" % params)
        self.writeresponse(' '.join(params))

    @command('user')
    def command_user(self, params):
        LOG.debug("User auth command")
        self.writeresponse('')

    @command('quit')
    def command_quit(self, params):
        LOG.debug("quit called")
        self.writeresponse('quitting')
        os.kill(os.getpid(), signal.SIGINT)


def signal_handler(signal, frame):
    LOG.info("Ctrl+C, exiting.")
    # sys.exit(0)  # thread ignores this
    os._exit(0)


# Setup the logging faciility
# to disable logging to stdout, but still log to file
# use the --quiet option on the cmdln
def setup_logging(args):
    global LOG
    levels = {
        'CRITICAL': logging.CRITICAL,
        'ERROR': logging.ERROR,
        'WARNING': logging.WARNING,
        'INFO': logging.INFO,
        'DEBUG': logging.DEBUG}
    log_level = levels[args.loglevel]

    LOG.setLevel(log_level)
    log_format = ("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]"
                  " %(message)s")
    date_format = '%m/%d/%Y %I:%M:%S %p'
    log_formatter = logging.Formatter(fmt=log_format,
                                      datefmt=date_format)
    fh = RotatingFileHandler('aprs-server.log',
                             maxBytes=(10248576 * 5),
                             backupCount=4)
    fh.setFormatter(log_formatter)
    LOG.addHandler(fh)

    if not args.quiet:
        sh = logging.StreamHandler(sys.stdout)
        sh.setFormatter(log_formatter)
        LOG.addHandler(sh)


class ClientThread(threading.Thread):
    def __init__(self, msg_q, ip, port, conn, *args, **kwargs):
        super(ClientThread, self).__init__()
        self.msg_q = msg_q
        self.ip = ip
        self.port = port
        self.conn = conn
        LOG.info("[+] New thread started for %s:%s" % (ip, port))

    def send_command(self, msg):
        LOG.info("Sending command '%s'" % msg)
        self.conn.send(msg)

    def run(self):
        while True:
            LOG.debug("Wait for data")
            readable, writeable, exceptional = select.select([self.conn],
                                                             [], [],
                                                             1)
            LOG.debug("select returned %s" % readable)
            if readable:
                data = self.conn.recv(2048)
                LOG.info("got data '%s'" % data)
            else:
                try:
                    msg = self.msg_q.get(True, 0.05)
                    if msg:
                        LOG.info("Sending message '%s'" % msg)
                        self.conn.send(msg + "\n")
                except Queue.Empty:
                    pass


class InputThread(threading.Thread):
    def __init__(self, msg_q):
        super(InputThread, self).__init__()
        self.msg_q = msg_q
        LOG.info("User input thread started")

    def run(self):
        while True:
            text = raw_input("Prompt> ")
            LOG.debug("Got input '%s'" % text)
            if text == 'quit':
                LOG.info("Quitting Input Thread")
                sys.exit(0)
            else:
                LOG.info("add '%s' to message Q" % text)
                self.msg_q.put(text)


threads = []


def main(args):
    global CONFIG, threads
    setup_logging(args)
    LOG.info("Test APRS server starting.")
    time.sleep(1)
    signal.signal(signal.SIGINT, signal_handler)

    CONFIG = utils.parse_config(args)

    msg_q = Queue.Queue()

    tcpsock = socket.socket(socket.AF_INET,
                            socket.SOCK_STREAM)
    tcpsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    ip = CONFIG['aprs']['host']
    port = CONFIG['aprs']['port']
    LOG.info("Start server listening on %s:%s" % (args.ip, args.port))
    tcpsock.bind((ip, port))

    in_t = None
    while True:
        tcpsock.listen(4)
        LOG.info("Waiting for incomming connections....")
        (conn, (ip, port)) = tcpsock.accept()
        newthread = ClientThread(msg_q, ip, port, conn)
        newthread.start()
        threads.append(newthread)
        if not in_t:
            in_t = InputThread(msg_q)
            in_t.daemon = True
            in_t.start()
            in_t.join()

    for t in threads:
        t.join()


if __name__ == "__main__":
    main(args)
