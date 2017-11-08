#!/usr/bin/env python

import logging
import asyncore
import socket
import operator
import threading
import time
import datetime
from functools import reduce
from geopy.geocoders import Nominatim


startutc = datetime.datetime(2018,3,4,9,43,27,320000)
delta = datetime.timedelta()
location = 'Budapest, Hungary'

geolocator = Nominatim()
geoloc = geolocator.geocode(location)
if not geoloc:
    raise ValueError('Requested location not found')

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
        zero = datetime.datetime.now()
        while self._stop == False:
            global delta
            delta = datetime.datetime.now() - zero
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
        # !!!!! EXAMPLE - ECHO
        # self.data_to_write.insert(0, data)
    
    def handle_close(self):
        self.logger.debug('handle_close()')
        self.t.stop()
        self.close()

def main():
    logging.basicConfig(level=logging.DEBUG, format='%(name)s:[%(levelname)s]: %(message)s')
    HOST = '0.0.0.0'
    PORT = 9999
    s = Server((HOST,PORT))
    asyncore.loop(1)


if __name__ == '__main__':
    main() 


