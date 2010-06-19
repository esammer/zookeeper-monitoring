#! /usr/bin/env python
""" Check Zookeeper Cluster

Generic monitoring script that could be used with multiple platforms.

It requires ZooKeeper 3.4.0 or greater or patch ZOOKEEPER-744
"""

import sys
import socket
import logging

from StringIO import StringIO
from optparse import OptionParser

__version__ = (0, 1, 0)

log = logging.getLogger()
logging.basicConfig(level=logging.DEBUG)

class ZooKeeperServer(object):

    def __init__(self, host='localhost', port='2181', timeout=1):
        self._address = (host, int(port))
        self._timeout = timeout

    def get_stats(self):
        """ Get ZooKeeper server stats as a map """
        s = self._create_socket()
        s.settimeout(self._timeout)

        s.connect(self._address)
        s.send('mntr')

        data = s.recv(2048)
        s.close()

        return self._parse(data)

    def _create_socket(self):
        return socket.socket()

    def _parse(self, data):
        """ Parse the output from the 'mntr' 4letter word command """
        h = StringIO(data)
        
        result = {}
        for line in h.readlines():
            try:
                key, value = self._parse_line(line)
                result[key] = value
            except ValueError:
                pass # ignore broken lines

        return result

    def _parse_line(self, line):
        try:
            key, value = map(str.strip, line.split('\t'))
        except ValueError:
            raise ValueError('Found invalid line: %s' % line)

        if not key:
            raise ValueError('The key is mandatory and should not be empty')

        try:
            value = int(value)
        except (TypeError, ValueError):
            pass

        return key, value

def main():
    opts, args = parse_cli()

    if opts.output is None:
        dump_stats(get_cluster_stats(opts.servers))


def dump_stats(cluster_stats):
    for server, stats in cluster_stats.items():
        print 'Server:', server

        for key, value in stats.items():
            print "%30s" % key, ' ', value
        print

def get_cluster_stats(servers):
    stats = {}
    for host, port in servers:
        try:
            zk = ZooKeeperServer(host, port)
            stats["%s:%s" % (host, port)] = zk.get_stats()

        except socket.error, e:
            # ignore because the cluster can still work even 
            # if few servers fail completely 

            logging.info('unable to connect to server '\
                '"%s" on port "%s"' % (host, port))

    return stats

def get_version():
    return '.'.join(map(str, __version__))

def parse_cli():
    parser = OptionParser(usage='./check_zookeeper.py <options>', version=get_version())

    parser.add_option('-s', '--servers', dest='servers', 
        help='a list of SERVERS', metavar='SERVERS')

    parser.add_option('-k', '--key', dest='key', 
        help='what KEY to analyze', metavar='KEY')

    parser.add_option('-w', '--warning', dest='warning', 
        help='WARNING level', metavar='WARNING')

    parser.add_option('-c', '--critical', dest='critical',
        help='CRITICAL level', metavar='CRITICAL')

    parser.add_option('-o', '--output', dest='output', 
        help='output HANDLER: nagios, ganglia, cacti', metavar='HANDLER')

    opts, args = parser.parse_args()

    if opts.servers is None:
        parser.error('The list of servers is mandatory')

    opts.servers = [s.split(':') for s in opts.servers.split(',')]

    return (opts, args)

if __name__ == '__main__':
    sys.exit(main())
