###############################################################################
# server-python.py
# Name:
# NetId:
###############################################################################

import sys
import socket

RECV_BUFFER_SIZE = 2048
QUEUE_LENGTH = 10

import datetime
import random  # for random seqyence number
import logging  # for logging information
import socket  # for sockets
import sys  # for exit
import pickle  # for serialization
import time  # for sleep and time
class UDP:
    def __init__(self, TCP):
        self.sourcePort = 0x0000  # 16 bits used
        self.destinationPort = 0x0000  # 16 bits used
        self.length = 0x0000  # 16 bits used
        self.checksum = 0x0000  # 16 bits used
        self.data = TCP
class TCP:
    def __init__(self):
        self.sourcePort = 0x0000  # 16 bits used
        self.destinationPort = 0x0000  # 16 bits used
        self.seqNumber = 0x00000000  # 32 bits used
        self.ackNumber = 0x00000000  # 32 bits used
        self.headerLength = 0b0000  # 4 bits used
        self.reserved = 0b000000  # 6 bit used
        self.URG = 0b0  # 1 bit used
        self.ACK = 0b0  # 1 bit used
        self.PSH = 0b0  # 1 bit used
        self.RST = 0b0  # 1 bit used
        self.SYN = 0b0  # 1 bit used
        self.FIN = 0b0  # 1 bit used
        self.receiveWindow = 0x0000  # 16 bits used
        self.checksum = 0x0000  # 16 bits used
        self.urgentPointer = 0x0000  # 16 bits used
def sendUDP(sock, host, sourcePort, destinationPort, seqNumber, ackNumber, ACK, SYN, FIN):
    tcp = TCP()
    tcp.sourcePort = sourcePort
    tcp.destinationPort = destinationPort
    tcp.seqNumber = seqNumber
    tcp.ackNumber = ackNumber
    tcp.ACK = ACK
    tcp.SYN = SYN
    tcp.FIN = FIN
    tcp.checksum = getChecksum(tcp)
    udp = UDP(tcp)
    udp.sourcePort = sourcePort
    udp.destinationPort = destinationPort
    sock.sendto(pickle.dumps(udp), (host, destinationPort))
def recvUDP(sock):
    data, addr = sock.recvfrom(1024)
    udp = pickle.loads(data)
    return [udp, addr]
def getChecksum(tcp):
    chSum = tcp.sourcePort + tcp.destinationPort
    protocol = (tcp.URG << 5) + (tcp.ACK << 4) + (tcp.PSH << 3) + (tcp.RST << 2) + (tcp.SYN << 1) + tcp.FIN
    chSum += protocol
    if chSum >= 2**16:
        chSum = (chSum >> 16) + chSum
    return ~(chSum & 0xFFFF)

def server(server_port):
    """TODO: Listen on socket and print received message to sys.stdout"""
    host = ''  # Symbolic name meaning all available interfaces
    port = server_port  # Arbitrary non-privileged port
    # Datagram (udp) socket
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # print 'Socket created.'
    except socket.error, msg:
        print 'Failed to create socket. Error Code : ' + str(msg[0]) + ' Message ' + msg[1]
        sys.exit()
    # Bind socket to local host and port
    try:
        sock.bind((host, port))
    except socket.error, msg:
        print 'Bind failed. Error Code : ' + str(msg[0]) + ' Message ' + msg[1]
        sys.exit()
    # print 'Socket bind complete.'
    # now keep talking with the
    y = 0  # sequence number of server
    connected = []  # keeps track of connected clients
    state = 'INIT'
    serverFile = open('server-log.txt', 'w')
    while True:
        udp, addr = recvUDP(sock)  # receive data from client
        if udp.data.checksum != getChecksum(udp.data): continue  # error detected
        if state == 'INIT' and udp.data.SYN == 1:  # request connection
            y = random.randint(1, 100)
            x = udp.data.seqNumber
            sendUDP(sock, addr[0], port, addr[1], seqNumber=y, ackNumber=x + 1, ACK=1, SYN=1, FIN=0)
            state = 'SYN-SENT'
        elif state == 'SYN-SENT' and udp.data.ACK == 1 and udp.data.ackNumber == y + 1:  # connection establishment
            connected.append(udp.data.sourcePort)
            print 'Client ' + str(addr[1]) + ' connected.'
            state = 'ESTAB'
        elif state == 'ESTAB' and udp.data.FIN != 1:  # packet received
            #if udp.data.seqNumber - x == 20:
                #continue
            sendUDP(sock, addr[0], port, addr[1], seqNumber=0, ackNumber=udp.data.seqNumber, ACK=1, SYN=0, FIN=0)
            # print str(datetime.datetime.now().time()) + ': Packet ' + str(udp.data.seqNumber) + ' received.'
            serverFile.write('Packet ' + str(udp.data.seqNumber) + ' received.\n')
        elif state == 'ESTAB' and udp.data.FIN == 1:  # request termination
            sendUDP(sock, addr[0], port, addr[1], seqNumber=0, ackNumber=udp.data.seqNumber + 1, ACK=1, SYN=0, FIN=0)
            sendUDP(sock, addr[0], port, addr[1], seqNumber=y, ackNumber=0, ACK=0, SYN=0, FIN=1)
            state = 'CLOSE-WAIT'
        elif state == 'CLOSE-WAIT' and udp.data.ACK == 1 and udp.data.ackNumber == y + 1:  # termination accepted
            print 'Connection closed.'
            break
    sock.close()
    serverFile.close()
    pass

def main():
    """Parse command-line argument and call server function """
    if len(sys.argv) != 2:
        sys.exit("Usage: python server-python.py [Server Port]")
    server_port = int(sys.argv[1])
    server(server_port)

if __name__ == "__main__":
    main()
