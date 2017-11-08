#!/usr/bin/env python

import socket
import operator
from functools import reduce

class nmea:
    contents = ''
    def __init__(self, conts):
        self.contents = conts
    def checksum(self):
        return "%0.2X" % reduce(lambda x,y:operator.xor(x,y), map(ord, self.contents))
    def tostring(self):
        return '$' + self.contents + '*' + str(self.checksum())


gga = nmea('GPGGA,094327.32,4851.4573,N,00218.0124,E,1,12,01.0,0.0,M,43.857,M,,')
print(gga.tostring())
rmc = nmea('GPRMC,094327.32,A,4851.4573,N,00218.0124,E,027.0,134.6,170217,003.1,W,A')
print(rmc.tostring())

static_sentences = [ nmea('GPGSA,A,3,01,02,03,04,05,06,,,,,,,001.0,001.0,001.0'),
        nmea('GPGSV,3,1,12,01,59,041,020,02,50,047,009,03,39,292,027,04,67,259,007'),
        nmea('GPGSV,3,2,12,05,67,099,006,06,49,103,029,07,40,015,018,08,02,187,012'),
        nmea('GPGSV,3,3,12,09,00,353,017,10,44,147,001,11,88,011,012,12,57,193,024') ]

for s in static_sentences:
    print(s.tostring())


TCP_IP = '127.0.0.1'
TCP_PORT = 9999
BUFFER_SIZE = 20  # Normally 1024, but we want fast response

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((TCP_IP, TCP_PORT))
s.listen(1)

conn, addr = s.accept()
print('Connection address: %s' % str(addr))
while 1:
    data = conn.recv(BUFFER_SIZE)
    if not data: break
    print("received data: %s" % str(data))
    conn.send(str(data).upper().encode())  # echo
conn.close()

