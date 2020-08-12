from collections import defaultdict
import time
class Client:
    def __init__(self, IP):
        global clients, g
        self.IP = IP  # from 0.0.0.0 to 255.255.255.255
        for c in clients:
            if IP == c.IP: # same IP
                g.write('Error: repeated client IP\n')
                self.IP = 'INVALID'
        self.connectedRouter = ""  # no router
        self.connectedLink = Link("0", "0", 0)  # no link
    def connectToRouter(self, r, l): # updates connected router and link
        self.connectedRouter = r
        self.connectedLink = l
class Router:
    def __init__(self, ID): # the router initial constructor
        global routers, g
        self.ID = ID  # from 1000 to 9999
        for r in routers:
            if ID == r.ID: # same ID
                g.write('Error: repeated router ID\n')
                self.ID = 'INVALID'
        if int(ID) >= 0 and (int(ID) < 1000 or int(ID) > 9999): # out of range ID
            g.write('Error: out of range router ID\n')
            self.ID = 'INVALID'
        self.neighbors = []  # no neighbors
        self.sendTimer = []  # keeps track of the packet sending time to neighbors
        self.recvTimer = []  # keeps track of the packet receiving time from neighbors
        self.interface = []  # no interface
        self.counter = 0  # the number of used interfaces
        self.RT = defaultdict(lambda: -1)  # the routing table
        self.LSDB = []  # the link state database
    def addClient(self, l): # connects to the client
        cID = l.head
        self.neighbors.append(cID) # adds the client to its neighbors
        self.sendTimer.append(-1) # sets -1 to timer so it will never get busted
        self.recvTimer.append(-1) # sets -1 to timer so it will never get busted
        self.interface.append(l) # sets the interface to link
        self.LSDB.append(l) # adds the link to its link state database
        self.upgrade() # updates the routing table
        c = findClient(cID) # finds the client
        self.initflood(c) # floods the change to network
    def establish(self, l): # handles the establishment of two routers
        global monitor, g
        if l.state[0] == "Down" and l.state[1] == "Down":
            if self.counter >= 10:  # full interface capacity
                g.write("Error: full interface capacity for router " + self.ID + '\n')
                return False
            self.interface.append(l)  # connects the new link to a new interface
            self.counter += 1  # adds a new interface
            p = Packet(self.ID, l.tail, "Hello", self.neighbors)  # Hello packet from router 1
            l.state[0] = "Init"  # changes sender state to Init
            return p
        elif l.state[0] == "Init" and l.state[1] == "Down":
            if monitor:  # prints received packet in case of monitor
                g.write(self.ID + " : " + l.pkt.type + " " + l.pkt.sender + " ")
                for n in l.pkt.body:
                    print(n + " ")
                g.write("\n")
            self.neighbors.append(l.pkt.sender)  # adds router 1 ID to his own neighbors
            self.sendTimer.append(10)  # sets sending timer for this neighbor to 10
            self.recvTimer.append(30)  # sets receiving timer for this neighbor to 30
            if self.counter >= 10:  # full interface capacity
                g.write("Error: full interface capacity for router " + self.ID + '\n')
                return False
            self.interface.append(l)  # connects the new link to a new interface
            self.counter += 1  # adds a new interface
            p = Packet(self.ID, l.pkt.sender, "Hello", self.neighbors)  # Hello packet from router 2
            l.state[1] = "Init"  # changes receiver state to Init
            return p
        elif l.state[0] == "Init" and l.state[1] == "Init":
            if monitor:  # prints received packet in case of monitor
                g.write(self.ID + " : " + l.pkt.type + " " + l.pkt.sender + " ")
                for n in l.pkt.body:
                    print(n + " ")
                g.write("\n")
            sender = findRouter(l.pkt.sender)
            if not (self.ID in sender.neighbors):
                print("Error: the sender ID is NOT in receiver neighbors")
                return False
            self.neighbors.append(l.pkt.sender)  # adds router 2 ID to his own neighbors
            self.sendTimer.append(10)  # sets sending timer for this neighbor to 10
            self.recvTimer.append(30)  # sets receiving timer for this neighbor to 30
            p = Packet(self.ID, l.pkt.sender, "Hello", self.neighbors)  # Hello packet from router 1
            l.state[0] = "2-way"  # changes sender state to 2-way
            return p
        elif l.state[0] == "2-way" and l.state[1] == "Init":
            if monitor:  # prints received packet in case of monitor
                g.write(self.ID + " : " + l.pkt.type + " " + l.pkt.sender + " ")
                for n in l.pkt.body:
                    print(n + " ")
                g.write("\n")
            sender = findRouter(l.pkt.sender)
            if not (self.ID in sender.neighbors):
                print("Error: the sender ID is NOT in receiver neighbors")
                return False
            l.state[1] = "2-way"  # changes receiver state to 2-way
            return None
        elif l.state[0] == 'full' and l.state[1] == 'full':
            if monitor:  # prints received packet in case of monitor
                g.write(self.ID + " : " + l.pkt.type + " " + l.pkt.sender + " ")
                for n in l.pkt.body:
                    g.write(n + " ")
                g.write("\n")
    def shareDBD(self, l): # handles the share of database between neighbors
        global monitor, g
        if l.state[0] == '2-way' and l.state[1] == '2-way':
            p = Packet(self.ID, l.pkt.sender, "DBD", self.LSDB)  # Hello packet from router 1
            l.state[1] = 'full-wait'  # changes sender state to full-wait
            return p
        elif l.state[0] == '2-way' and l.state[1] == 'full-wait':
            if monitor:  # prints received packet in case of monitor
                g.write(self.ID + " : " + l.pkt.type + " " + l.pkt.sender + " ")
                for n in l.pkt.body:
                    g.write(n.head + " " + n.tail + ' ' + str(n.cost) + ' *** ')
                g.write("\n")
            sender = findRouter(l.pkt.sender)  # finds sender of the packet
            self.LSDB.append(l)  # adds the new link to link state database
            self.LSDB = list(set(self.LSDB) | set(sender.LSDB))  # merges two database
            self.initflood(sender.ID) # initiates flood to neighbors
            self.upgrade() # updates the routing table
            p = Packet(self.ID, l.pkt.sender, "DBD", self.LSDB)  # DBD packet from router 1
            l.state[0] = 'full'  # changes sender state to full
            return p
        elif l.state[0] == 'full' and l.state[1] == 'full-wait':
            if monitor:  # prints received packet in case of monitor
                g.write(self.ID + " : " + l.pkt.type + " " + l.pkt.sender + " ")
                for n in l.pkt.body:
                    g.write(n.head + " " + n.tail + ' ' + str(n.cost) + ' *** ')
                g.write("\n")
            sender = findRouter(l.pkt.sender)  # finds sender of the packet
            self.LSDB.append(l)  # adds the new link to link state database
            self.LSDB = list(set(self.LSDB) | set(sender.LSDB))  # merges two database
            self.initflood(sender.ID) # initiates flood to neighbors
            self.upgrade() # updates the routing table
            p = Packet(self.ID, l.pkt.sender, "DBD", self.LSDB)  # DBD packet from router 1
            l.state[1] = 'full'  # changes sender state to full
            return p
    def initflood(self, waver): # the initial flood of a router
        for nei in self.neighbors:
            if mode(nei) != 'router': # ensures to send data only to routers
                continue
            n = findRouter(nei)
            if n.ID != waver: # not the waver
                p = Packet(self.ID, n.ID, 'LSA', self.LSDB)  # LSA packet from router
                n.flood(p) # floods to the neighbor
    def flood(self, p): # floods the change to neighbors
        global monitor
        if monitor:  # prints received packet in case of monitor
                g.write(self.ID + " : " + p.type + " " + p.sender + " ")
                for n in p.body:
                    g.write(n.head + " " + n.tail + ' ' + str(n.cost) + ' *** ')
                g.write("\n")
        if set(self.LSDB) == set(p.body): # drop
            return
        # deletes damaged links
        newLSDB = []
        for l in self.LSDB:
            if l.isCorrupt != True:
                newLSDB.append(l)
        self.LSDB = newLSDB
        self.LSDB = list(set(self.LSDB) | set(p.body)) # merges the databases
        self.upgrade() # updates the routing table
        parent = findRouter(p.sender) # finds who sent this flood message
        for nei in self.neighbors:
            if mode(nei) != 'router': # ensures to send data only to routers
                continue
            l = findLink(nei, self.ID) # finds link between neighbors
            if l.isCorrupt == True: # ignores the damaged links
                continue
            n = findRouter(nei)
            if n.ID != parent.ID:
                p = Packet(self.ID, n.ID, 'LSA', self.LSDB)  # LSA packet from router
                n.flood(p) # floods to the neighbor
    def stillConnected(self, l): # receives the 10-second-send information
        i = 0
        global monitor, g
        if monitor:  # prints received packet in case of monitor
            g.write(self.ID + " : " + l.pkt.type + " " + l.pkt.sender + " ")
            for n in l.pkt.body:
                g.write(n + " ")
            g.write('\n')
        for i in range(len(self.neighbors)): # find the index of the sender
            if self.neighbors[i] == l.pkt.sender:
                break
        self.recvTimer[i] = 30 # resets the receiving timer
        return
    def dec(self): # decrements the router timers after 1 second
        for i in range(len(self.recvTimer)):
            self.recvTimer[i] -= 1 # one second passes
            self.sendTimer[i] -= 1 # one second passes
    def check(self): # updates the router information after 1 second
        for i in range(len(self.sendTimer)):
            if self.sendTimer[i] == 0: # time to send packet again to neighbor[i]
                self.sendTimer[i] = 10 # resets the sending timer
                p = Packet(self.ID, self.neighbors[i], 'Hello', self.neighbors)  # Hello packet from router
                l = self.interface[i] # the link connecting the router to its desired neighbor
                recv = l.deliver(p) # delivers the package
                if recv != None:
                    recv.stillConnected(l) # the receiver router gets the packet
        deletingList = []
        for i in range(len(self.recvTimer)):
            #print('___________________________' + self.ID + ' | ' + str(i) + '_______________________________')
            if self.recvTimer[i] == 0: # no packet recived from neighbor[i]
                deletingList.append(i) # adds i to deleting list
                #self.sendTimer.__delitem__(i) # removes the sending time variable
                #self.recvTimer.__delitem__(i) # removes the receiving time variable
                sender = findRouter(self.neighbors[i]) # finds the other end router
                #self.neighbors.__delitem__(i) # removes the router from neighbors
                l = self.interface[i] # the supposedly damaged link
                #self.interface.__delitem__(i) # removes the interface for that link
                if not(l in self.LSDB):
                    continue
                self.LSDB.remove(l) # removes link l from its link state database
                self.upgrade() # updates the routing table
                self.initflood(sender.ID) # initiates flood to neighbors
        newSendTimer, newRecvTimer, newNeighbors, newInterface = [], [], [], []
        for i in range(len(self.recvTimer)):
            if not(i in deletingList):
                newSendTimer.append(self.sendTimer[i])
                newRecvTimer.append(self.recvTimer[i])
                newNeighbors.append(self.neighbors[i])
                newInterface.append(self.interface[i])
        self.sendTimer = newSendTimer
        self.recvTimer = newRecvTimer
        self.neighbors = newNeighbors
        self.interface = newInterface
        self.upgrade()
    def dijkstra(self): # runs the dijkstra algorithm on the local LSDB
        child, cost = graph(self.LSDB) # constructs the corresponding graph
        # initiation
        u = self.ID
        N = [u]
        D = {}
        p = {}
        for c in child:
            if c in child[u]:
                D[c] = cost[(c, u)]
                p[c] = u
            elif c == u:
                D[c] = 0
                p[c] = ''
            else:
                D[c] = float('inf')
                p[c] = ''
        # loop
        while len(N) != len(child):
            # finds w not in N with minimum D[w]
            minCost = float('inf')
            for n in child:
                if not(n in N) and D[n] < minCost:
                    w = n
                    minCost = D[w]
            # adds w to N
            N.append(w)
            # update D[v] for all v adjacent to w and not in N
            for v in child[w]:
                if not(v in N):
                    if D[v] >= D[w] + cost[(v, w)]:
                        p[v] = w
                        D[v] = D[w] + cost[(v, w)]
        # removes the unconnected routers
        D2, p2 = {}, {}
        for x in D:
            if D[x] != float('inf'):
                D2[x] = D[x]
                p2[x] = p[x]
        return D2, p2
    def upgrade(self): # updates routing table
        self.RT = {}
        D, p = self.dijkstra() # gets the distance and parent
        #print('xxxxxxxxxxxxxxxxxxxxxxxxx')
        #print(self.ID)
        #print(D)
        #print(p)
        #print('xxxxxxxxxxxxxxxxxxxxxxxxx')
        u = self.ID
        for v in D:
            w = v
            if w == u:
                continue
            while p[w] != u:
                w = p[w]
            for i in range(len(self.interface)): # searches in all interfaces to find the 
                l = self.interface[i] # gets the link of the interface
                if l.head == w or l.tail == w: # checks whether this link is connected to w
                    self.RT[v] = i # maps the router to the desired interface
                    break
        # adds his client to routing table
        for i in range(len(self.neighbors)):
            #print('ooooooooooooooooooooooooooooooooooooooooooo')
            #print(self.ID)
            if mode(self.neighbors[i]) == 'client':
                #print('zzzzzzzzzzzzzzzzzzzzzzzzz')
                self.RT[self.neighbors[i]] = i        
class Packet:
    def __init__(self, sender, receiver, type, body):
        self.sender = sender  # the packet sender
        self.receiver = receiver  # the packet receiver
        self.type = type  # the packet type [LSA, DBD, Hello, ping]
        self.body = body  # the message body
class Link:
    def __init__(self, head, tail, cost):
        self.isCorrupt = False  # indicates corruptness of link
        self.cost = cost  # cost of the link
        self.head = head # contains head router or client
        self.tail = tail # contains tail router or client
        self.state = ["Down", "Down"]  # contains state of the head and tail router
        self.pkt = Packet("0", "0", "", "")  # the potential packet in the link
    def deliver(self, p):
        self.pkt = p  # give packet to link
        if self.isCorrupt:
            return None  # return if the link is corrupted
        recv = findRouter(p.receiver)
        return recv
def findRouter(ID): # finds router by its ID
    global routers
    for r in routers:
        if r.ID == ID:
            return r
def findClient(IP): # finds router by its ID
    global clients
    for c in clients:
        if c.IP == IP:
            return c
def findLink(x, y): # finds link between x and y
    global links
    for l in links:
        if (l.head == x and l.tail == y) or (l.head == y and l.tail == x):
            return l
def mode(x): # checks if this is a router or a client
    global router, clients
    for r in routers:
        if x == r.ID:
            return 'router'
    for c in clients:
        if x == c.IP:
            return 'client'
    return 'none'
def connectRouters(ID1, ID2, l):
    global clients, routers, links, monitor
    head = findRouter(ID1)  # finds sender router
    # sender
    p = head.establish(l)  # establishes new connection via link l and returns the packet
    # link (1st Hello transfer)
    tail = l.deliver(p)  # delivers
    # receiver
    p = tail.establish(l)  # receives the 1st Hello and returns the packet
    # link (2nd Hello transfer)
    head = l.deliver(p)  # delivers
    # sender
    p = head.establish(l)  # receives the 2nd Hello and returns the packet
    # link (3rd Hello transfer)
    tail = l.deliver(p)  # delivers
    # receiver
    p = tail.establish(l)
    p = tail.shareDBD(l)
    # link (1st DBS transfer)
    head = l.deliver(p)
    # sender
    p = head.shareDBD(l)
    # link (2nd DBS transfer)
    tail = l.deliver(p)
    # sender
    p = tail.shareDBD(l)
def connectClient(IP, ID, cost): # coonects client cID to router rID:
    c = findClient(IP) # finds client
    r = findRouter(ID) # finds router
    l = Link(IP, ID, cost)  # create a new link between routers
    r.addClient(l) # add the client to router r
    c.connectToRouter(ID, l) # updates client link
def graph(LSDB): # constructs a graph based on links
    child = defaultdict(lambda: [])
    cost = {}
    for l in LSDB:
        head = l.head
        tail = l.tail
        c = l.cost
        child[head].append(tail) # adds to child
        child[tail].append(head) # adds to child
        cost[(head, tail)], cost[(tail, head)] = c, c # sets cost
    return child, cost
def ping(s, t): # pings path from s to t
    global monitor, g, p
    g.write(s + ' ')
    p.write(s + ' ')
    if s == t: # recursive termination
        g.write('\n')
        p.write('\n')
        return
    source = findRouter(s) # finds router s
    if not(t in source.RT): # can not find target
        g.write('invalid\n')
        p.write('invalid\n')
        return
    i = source.RT[t] # gets interface
    l = source.interface[i] # gets link
    if l.isCorrupt == True: # damaged link
        g.write('unreachable\n')
        p.write('unreachable\n')
        return
    if l.head != source.ID: # finds the other end
        ping(l.head, t)
        if monitor:  # prints received packet in case of monitor
            g.write(l.head + " : " + 'ping' + " " + s + " " + t + '\n')
    else:
        ping(l.tail, t)
        if monitor:  # prints received packet in case of monitor
            g.write(l.tail + " : " + 'ping' + " " + s + " " + t + '\n')
    return
def main():
    global routers, clients, links, monitor, g, p
    print('Enter \'exit\' to end program')
    while True:
        lst = input().split()
        if lst[0] == "add" and lst[1] == "router":
            if Router(lst[2]).ID != 'INVALID': # if valid router ID
                routers.append(Router(lst[2]))
        elif lst[0] == "add" and lst[1] == "client":
            if Client(lst[2]).IP != 'INVALID': # if valid client IP
                clients.append(Client(lst[2]))
        elif lst[0] == "connect":
            if mode(lst[1]) == 'router': # the first argument is a router
                ID1, ID2, cost = lst[1], lst[2], int(lst[3])
                l = Link(ID1, ID2, cost)  # create a new link between routers
                links.append(l) # adds the new link to all links list
                connectRouters(ID1, ID2, l)
            elif mode(lst[1]) == 'client': # the first argument is a client
                connectClient(lst[1], lst[2], int(lst[3]))
            else:
                g.write('Error: invalid input\n')
        elif lst[0] == 'sec':
            sec = int(lst[1])
            if sec <= 0:
                g.write('Error: invalid time entered\n')
            else:
                for j in range(sec):
                    for r in routers:
                        r.dec()
                    for r in routers:
                        r.check()
        elif lst[0] == 'ping':
            s, target = lst[1], lst[2]
            g.write(s + ' ')
            p.write(s + ' ')
            c = findClient(s) # finds client c
            if c.connectedRouter == '':
                g.write('invalid\n')
                p.write('invalid\n')
            else:
                source = c.connectedRouter # the connected router to c
                if monitor:  # prints received packet in case of monitor
                    g.write(source + " : " + 'ping' + " " + s + " " + target + '\n')
                ping(source, target)
        elif lst[0] == 'link':
            x, y = lst[1], lst[2]
            l = findLink(x, y)
            if lst[3] == 'd':
                l.isCorrupt = True
                l.state[0], l.state[1] = 'Down', 'Down'
            elif lst[3] == 'e':
                l.isCorrupt = False
                connectRouters(l.head, l.tail, l)
        elif lst[0] == 'monitor':
            if lst[1] == 'e':
                monitor = True
            elif lst[1] == 'd':
                monitor = False
        elif lst[0] == 'exit':
            break
        continue # for all information printing (It's so messy. Ignore it)
        for r in routers:
            print('---------------------------------------------------')
            print('ID :', r.ID)
            print('Interface: ', end = '')
            for i in range(len(r.interface)):
                print(str(i) + ' : ' + r.interface[i].head + ' <-> ' + r.interface[i].tail + ' *** ', end = '')
            print('')
            print('Nerighbors: ', end = '')
            for n in range(len(r.neighbors)):
                print(r.neighbors[n] + ' ' + str(r.sendTimer[n]) + ' ' + str(r.recvTimer[n]) + ' *** ', end = '')
            print('')
            print('LSDB: ', end = '')
            for l in r.LSDB:
                print(l.head, l.state[0], l.tail, l.state[1], l.cost, ' *** ', end = '')
            print('')
            print('RT: ', end = '')
            for x in r.RT:
                print(x + '->' + str(r.RT[x]) + ' *** ', end = '')
            print('')
        for l in links:
            print(l.head, l.state[0], l.tail, l.state[1], l.cost)
routers = []
clients = []
links = []
monitor = False
g = open('out.txt', 'w')
p = open('pingOut.txt', 'w')
if __name__ == "__main__":
    main()