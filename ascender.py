#!/usr/bin/env python3

import socket

class Client(object):

    def __init__(self, address, port):
        self.address = address
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connect()
        self.sock.close()

    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.sock.connect((self.address, self.port))
        except:
            raise

    def send(self, message):
        try:
            self.connect()
            self.sock.sendall(message.encode('utf-8'))
        except:
            raise

        resp = "" 
        while 1:
            r = self.sock.recv(256)
            if not r:
                self.sock.close()
                return resp.rstrip()
            else:
                rs = r.decode('utf-8')
                resp += rs
                continue
