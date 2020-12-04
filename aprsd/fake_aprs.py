import argparse
import logging
import sys
import time
import socketserver

from logging.handlers import RotatingFileHandler

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

CONFIG = None
LOG = logging.getLogger('ARPSSERVER')


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


class MyAPRSTCPHandler(socketserver.BaseRequestHandler):

    def handle(self):
        # self.request is the TCP socket connected to the client
        self.data = self.request.recv(1024).strip()
        LOG.debug("{} wrote:".format(self.client_address[0]))
        LOG.debug(self.data)
        # just send back the same data, but upper-cased
        self.request.sendall(self.data.upper())


def main():
    global CONFIG
    args = parser.parse_args()
    setup_logging(args)
    LOG.info("Test APRS server starting.")
    time.sleep(1)

    CONFIG = utils.parse_config(args)

    ip = CONFIG['aprs']['host']
    port = CONFIG['aprs']['port']
    LOG.info("Start server listening on %s:%s" % (args.ip, args.port))

    with socketserver.TCPServer((ip, port), MyAPRSTCPHandler) as server:
        server.serve_forever()


if __name__ == "__main__":
    main()
