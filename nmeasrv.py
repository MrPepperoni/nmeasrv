#!/usr/bin/env python

import logging
import asyncore
import socket
import operator
import threading
import time
import datetime
from functools import reduce


startutc = datetime.datetime(2017,2,17,9,43,27,320000)
print(startutc)

def timestr():
    return '094327.32'

def datestr():
    return '170217'

def posstr():
    return '4851.4573,N,00218.0124,E'

def speedstr():
    return '027.0,134.6'

class nmea:
    content = ''
    def __init__(self, conts):
        self.content = conts
    def checksum(self):
        return "%0.2X" % reduce(lambda x,y:operator.xor(x,y), map(ord, self.contents()))
    def tostring(self):
        return '$' + self.contents() + '*' + str(self.checksum()) + '\n'
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


gga = gga_sentence()
print(gga.tostring())
rmc = rmc_sentence()
print(rmc.tostring())

static_sentences = [ nmea('GPGSA,A,3,01,02,03,04,05,06,,,,,,,001.0,001.0,001.0'),
        nmea('GPGSV,3,1,12,01,59,041,020,02,50,047,009,03,39,292,027,04,67,259,007'),
        nmea('GPGSV,3,2,12,05,67,099,006,06,49,103,029,07,40,015,018,08,02,187,012'),
        nmea('GPGSV,3,3,12,09,00,353,017,10,44,147,001,11,88,011,012,12,57,193,024') ]

for s in static_sentences:
    print(s.tostring())


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
        while self._stop == False:
            self.client.enqueueData("data_thread")
            time.sleep(1)

class ClientHandler(asyncore.dispatcher):
    def __init__(self, sock, address):
        asyncore.dispatcher.__init__(self, sock)
        self.logger = logging.getLogger('Client ' + str(address))
        self.data_to_write = []
        self.t = SenderThread(self)
        self.t.start()

    def enqueueData(self, data):
        self.data_to_write.append(data.encode())

    def writable(self):
        return bool(self.data_to_write)

    def handle_write(self):
        data = self.data_to_write.pop()
        sent = self.send(data[:1024])
        if sent < len(data):
            remaining = data[sent:]
            self.data.to_write.append(remaining)
        self.logger.debug('handle_write() -> (%d) "%s"', sent, data[:sent].rstrip())

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


