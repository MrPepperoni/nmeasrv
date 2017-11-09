#!/usr/bin/env python

import logging
import asyncore
import socket
import operator
import threading
import time
import datetime
import argparse
from functools import reduce
from geopy.geocoders import Nominatim


startutc = datetime.datetime.now()
zeroutc = datetime.datetime.now()

geolocator = Nominatim()
geoloc = None

def switch_to(timest, locstr):
    global zeroutc
    global startutc
    global geoloc
    geoloc = None
    logger = logging.getLogger('Switch')
    if True:
        startutc = datetime.datetime.strptime(timest.strip(),"%Y-%m-%d %H:%M:%S.%f")
        zeroutc = datetime.datetime.now()
        geoloc = geolocator.geocode(locstr.strip())
        logger.info('Switched to %s %s', timest, locstr)
        return True
    if False:
        logger.warning('Cannot parse %s %s', timest, locstr)
        return False

def degrees(loc):
    return int(("%f" % abs(loc)).split('.')[0])

def minutes(loc):
    l = abs(loc)
    d = degrees(loc)
    r = l - d
    return r * 60.0

def lat(gc):
    # N: + S: -
    loc = gc.latitude
    return "%02d%07.4f,%s" % (degrees(loc), minutes(loc), (loc < 0 and 'S' or 'N'))

def lon(gc):
    # E: + W: -
    loc = gc.longitude
    return "%03d%07.4f,%s" % (degrees(loc), minutes(loc), (loc < 0 and 'W' or 'E'))

def curtime():
    delta = datetime.datetime.now() - zeroutc
    return startutc + delta

def timestr():
    t = curtime()
    return '%02i%02i%02i.%02i' % (t.hour, t.minute, t.second, t.microsecond // 10000)

def datestr():
    t = curtime()
    return '%02i%02i%02i' % (t.year % 100, t.month, t.day)

def posstr():
    return '%s,%s' % (lat(geoloc), lon(geoloc))

def speedstr():
    return '000.0,000.0'

class nmea:
    content = ''
    def __init__(self, conts):
        self.content = conts
    def checksum(self):
        return "%0.2X" % reduce(lambda x,y:operator.xor(x,y), map(ord, self.contents()))
    def tostring(self):
        return '$' + self.contents() + '*' + str(self.checksum()) + '\r\n'
    def contents(self):
        return self.content

class gga_sentence(nmea):
    def __init__(self):
        super(gga_sentence,self).__init__('')
    def contents(self):
        return 'GPGGA,' + timestr() + ',' + posstr() + ',1,12,01.0,0.0,M,43.857,M,,'

class rmc_sentence(nmea):
    def __init__(self):
        super(rmc_sentence,self).__init__('')
    def contents(self):
        return 'GPRMC,' + timestr() + ',A,' + posstr() + ',' + speedstr() + ',' + datestr() + ',003.1,W,A'


sentences = [ gga_sentence(),
        nmea('GPGSA,A,3,01,02,03,04,05,06,,,,,,,001.0,001.0,001.0'),
        nmea('GPGSV,3,1,12,01,59,041,020,02,50,047,009,03,39,292,027,04,67,259,007'),
        nmea('GPGSV,3,2,12,05,67,099,006,06,49,103,029,07,40,015,018,08,02,187,012'),
        nmea('GPGSV,3,3,12,09,00,353,017,10,44,147,001,11,88,011,012,12,57,193,024'),
        rmc_sentence() ]


class Server(asyncore.dispatcher):
    def __init__(self, address):
        asyncore.dispatcher.__init__(self)
        self.logger = logging.getLogger('Server')
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()
        self.bind(address)
        self.address = self.socket.getsockname()
        self.logger.debug('binding to %s', self.address)
        self.listen(5)

    def handle_accept(self):
        # Called when a client connects to our socket
        client_info = self.accept()
        if client_info is not None:
            self.logger.debug('handle_accept() -> %s', client_info[1])
            ClientHandler(client_info[0], client_info[1])

class SenderThread(threading.Thread):
    _stop = False

    def __init__(self, client):
        super(SenderThread,self).__init__()
        self.client = client

    def stop(self):
        self._stop = True

    def run(self):
        global geoloc
        while self._stop == False:
            if geoloc:
                for s in sentences:
                    self.client.enqueueData(s.tostring())
            time.sleep(1)

class ClientHandler(asyncore.dispatcher):
    def __init__(self, sock, address):
        asyncore.dispatcher.__init__(self, sock)
        self.m = threading.Lock()
        self.logger = logging.getLogger('Client ' + str(address))
        self.data_to_write = []
        self.t = SenderThread(self)
        self.t.start()

    def enqueueData(self, data):
        self.m.acquire()
        self.data_to_write.append(data.encode())
        self.m.release()

    def writable(self):
        return bool(self.data_to_write)

    def handle_write(self):
        self.m.acquire()
        while self.writable():
            data = self.data_to_write.pop(0)
            self.logger.debug('handle_write() -> "%s"', data.rstrip())
            while len(data) > 0:
                sent = self.send(data[:1024])
                data = data[sent:]
        self.m.release()

    def handle_read(self):
        data = self.recv(1024)
        self.logger.debug('handle_read() -> (%d) "%s"', len(data), data.rstrip())
    
    def handle_close(self):
        self.logger.debug('handle_close()')
        self.t.stop()
        self.close()

class TestCaseHandler(threading.Thread):
    _stop = False

    def __init__(self, infile):
        super(TestCaseHandler,self).__init__()
        self.infile = infile

    def stop(self):
        self._stop = True

    def run(self):
        for l in self.infile.readlines():
            if len(l) == 0 or l[0] == '#':
                continue
            parts = l.split('@')
            if len(parts) < 2:
                continue
            if not switch_to(parts[0],parts[1]):
                continue
            for i in range(5 * 60):
                if self._stop:
                    return
                time.sleep(1)  # wait 5 minutes
        logger = logging.getLogger('TC')
        logger.info('test case handler finished')



def main():
    logging.basicConfig(level=logging.DEBUG, format='%(name)s:[%(levelname)s]: %(message)s')

    parser = argparse.ArgumentParser(description='Create NMEA emulator tcp server')
    parser.add_argument('-p', '--port', dest='port', type=int,
                        default=9999,
                        help='port to listen on (default: 9999)')
    parser.add_argument('infile', type=argparse.FileType('r'))

    args = parser.parse_args()
    print(args.port)

    host = '0.0.0.0'
    s = Server((host,args.port))
    t = TestCaseHandler(args.infile)
    t.start()
    asyncore.loop(1)
    t.stop()


if __name__ == '__main__':
    main() 


