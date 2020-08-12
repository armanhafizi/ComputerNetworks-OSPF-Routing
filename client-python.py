###############################################################################
# client-python.py
# Name:
# NetId:
###############################################################################

import sys
import socket
import datetime
import random  # for random seqyence number
import threading  # for creating thread
import time  # for getting time
import socket  # for sockets
import sys  # for exit
import pickle  # for serialization

SEND_BUFFER_SIZE = 2048
host = 'localhost'  # server host
sport = 8888  # server port
cport = 0  # client port
x = 0  # sequence number of client
y = 0  # sequence number of server
state = 'INIT'  # initial state
estimatedRTT = 1  # estimated RTT
devRTT = 0  # deviation from estimated RTT
term = []  # terminated threads
acked = []  # acked packets
cwnd = 1  # congestion window
notAcked = 0  # the number of packets sent but not acked yet
timeOut = 1  # time out
resend = []  # resend the timed out packets
endProgramTime = 0  # flag for when to send FIN
x_seq = 0  # sequence for FIN
RTT = 0  # just for test!!!
clientFile = open('client-log.txt', 'w')
sampleRTTFile = open('sample-RTT-log.txt', 'w')
cwndFile = open('congestion-window-log.txt', 'w')
threads = []  # active threads

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
    return [udp, addr]# create dgram udp socket
def getChecksum(tcp):
    chSum = tcp.sourcePort + tcp.destinationPort
    protocol = (tcp.URG << 5) + (tcp.ACK << 4) + (tcp.PSH << 3) + (tcp.RST << 2) + (tcp.SYN << 1) + tcp.FIN
    chSum += protocol
    if chSum >= 2**16:
        chSum = (chSum >> 16) + chSum
    return ~(chSum & 0xFFFF)
def sendThread():
    global state, host, sport, cport, x, y, sock, timeOut, cwnd, notAcked, resend, endProgramTime, x_seq, RTT, threads
    p = 1  # packet number to be sent
    while True:
        if state == 'INIT':  # initial state
            with threading.Lock():
                x = random.randint(1, 100)
                sendUDP(sock, host, cport, sport, seqNumber=x, ackNumber=0, ACK=0, SYN=1, FIN=0)
            time.sleep(timeOut)
        elif state == 'SYN-RCVD':  # SYN received
            with threading.Lock():
                print 'Connection established.'
                sendUDP(sock, host, cport, sport, seqNumber=0, ackNumber=y+1, ACK=1, SYN=0, FIN=0)
                state = 'ESTAB'
        elif state == 'ESTAB' and endProgramTime == 0:  # connection established
            if notAcked < cwnd:
                with threading.Lock():
                    if len(resend) == 0:  # no timed out packets
                        packet = threading.Thread(target=packetThread, args=(p,))
                        p += 1
                    else:
                        head = resend[0]
                        resend = resend[1:]
                        packet = threading.Thread(target=packetThread, args=(head,))
                threads.append(packet)
                packet.start()
                time.sleep(0.1)
        elif state == 'ESTAB' and endProgramTime == 1:  # program time ends
            #print str(datetime.datetime.now().time()) + ': HERE'
            time.sleep(RTT)
            with threading.Lock():
                sendUDP(sock, host, cport, sport, seqNumber=x+p, ackNumber=0, ACK=0, SYN=0, FIN=1)
                x_seq = x+p
                state = 'FIN-WAIT-1'
        elif state == 'TIMED-WAIT':
            time.sleep(RTT)
            with threading.Lock():
                sendUDP(sock, host, cport, sport, seqNumber=0, ackNumber=y+1, ACK=1, SYN=0, FIN=0)
            time.sleep(2*timeOut)
            break
    clientFile.close()
    sampleRTTFile.close()
    cwndFile.close()
def recvThread():
    global state, host, sport, cport, x, y, sock, acked, cwnd, notAcked, timeOut, x_seq, RTT, cwndFile
    receiveFlag = 1
    while receiveFlag:
        try:
            udp, addr = recvUDP(sock)  # receive data from server
            if udp.data.checksum != getChecksum(udp.data): continue  # error detected
            elif udp.data.SYN == 1 and udp.data.ACK == 1 and udp.data.ackNumber == x+1 and state == 'INIT':
                with threading.Lock():
                    cport = udp.data.destinationPort
                    y = udp.data.seqNumber
                    state = 'SYN-RCVD'
            elif (state == 'ESTAB' or state == 'FIN-WAIT-1' or state == 'FIN-WAIT-2') and udp.data.ACK == 1 and udp.data.ackNumber != x_seq+1:
                with threading.Lock():
                    i = udp.data.ackNumber - x
                    if not(i in acked):  # new packet acked
                        acked.append(i)
                        notAcked -= 1
                        if cwnd < 20:
                            cwnd += 1
                        cwndFile.write(str(datetime.datetime.now().time()) + ': ' + str(cwnd) + '\n')
                        term.append(i)  # terminate packet i thread

            elif state == 'FIN-WAIT-1' and udp.data.ACK == 1:
                with threading.Lock():
                    state = 'FIN-WAIT-2'
            elif state == 'FIN-WAIT-2' and udp.data.FIN == 1:
                with threading.Lock():
                    y = udp.data.seqNumber
                    state = 'TIMED-WAIT'
                time.sleep(2 * timeOut)
                print 'Connection closed.'
                receiveFlag = 0
        except:
            continue
def packetThread(i):
    global state, host, sport, cport, x, y, sock, term, cwnd, timeOut, notAcked, resend, RTT, devRTT, estimatedRTT, clientFile, cwndFile, sampleRTTFile
    startTime = time.time()
    notAcked += 1
    #print str(datetime.datetime.now().time()) + ': Packet ' + str(x + i) + ' sent. ' + str(notAcked) + ' ' + str(cwnd)
    time.sleep(RTT)
    sendUDP(sock, host, cport, sport, seqNumber=x+i, ackNumber=0, ACK=0, SYN=0, FIN=0)
    while not(i in term):
        if time.time() - startTime >= timeOut:
            with threading.Lock():
                cwnd = int(cwnd/2)
                cwndFile.write(str(datetime.datetime.now().time()) + ': ' + str(cwnd) + '\n')
                notAcked -= 1
                resend.append(i)
                clientFile.write(str(datetime.datetime.now().time()) + ': Packet ' + str(x + i) + ' dropped.\n')
                #print str(datetime.datetime.now().time()) + ': Packet ' + str(x+i) + ' dropped: ' + str(time.time()-startTime) + ' secs'
            break
    if i in term:
        with threading.Lock():
            sampleRTT = time.time() - startTime
            sampleRTTFile.write(str(datetime.datetime.now().time()) + ': ' + str(sampleRTT) + '\n')
            #print str(datetime.datetime.now().time()) + ': Packet ' + str(x+i) + ' received: ' + str(sampleRTT) + ' secs ' + str(notAcked) + ' ' + str(cwnd)
            estimatedRTT = (1-0.125)*estimatedRTT + 0.125*sampleRTT
            devRTT = (1-0.25)*devRTT + 0.25*(abs(sampleRTT-estimatedRTT))
            timeOut = estimatedRTT + 4*devRTT
def programThread():
    global endProgramTime
    time.sleep(30)
    endProgramTime = 1

def client(server_ip, server_port):
    """TODO: Open socket and send message from sys.stdin"""
    global host, sport, sock, threads
    host = server_ip
    sport = server_port
    # main
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    except socket.error:
        print 'Failed to create socket'
        sys.exit()
    sender = threading.Thread(target=sendThread)
    receiver = threading.Thread(target=recvThread)
    program = threading.Thread(target=programThread)
    threads.append(sender)
    threads.append(receiver)
    threads.append(program)
    sender.start()
    receiver.start()
    program.start()
    pass


def main():
    """Parse command-line arguments and call client function """
    if len(sys.argv) != 3:
        sys.exit("Usage: python client-python.py [Server IP] [Server Port] < [message]")
    server_ip = sys.argv[1]
    server_port = int(sys.argv[2])
    client(server_ip, server_port)

if __name__ == "__main__":
    main()
