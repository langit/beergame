'''This module is for a text based Beer Game.
It is developed for teaching purpose only.

By Yingjie Lan (ylan@pku.edu.cn), Peking University

Date of latest update: 2016/4/27.

Permission is hereby granted, free of charge, to any
person obtaining a copy of this software and associated
documentation files (the "Software"), to deal in the
Software without restriction, including without
limitation the rights to use, copy, modify, merge,
publish, distribute, sublicense, and/or sell copies
of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the
following conditions:
The above copyright notice and this permission notice
shall be included in all copies or substantial portions
of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY
OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT
LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE
OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''

'''Beer Game

UI design: text based.

Protocal design:

the player connects to server.
the server asks for pass code, which is made of three parts:
    [game id]0[player id][pass code]
    the server confirms and admits player into a preconfigured game.
    three chances for the player to get it right.
the server enters a loop:
    1. send a message of player status in the beginning of a period
    2. ask for an order decision
    3. send updates of game status (who has submitted order)
    4. if all players have sent in their order, go to step 1 or end game.
'''


#for Python 3.5

import socket
import threading
import socketserver
import collections
import time
import random


##class que(list):
##    def __init__(self, *args):
##        list.__init__(self, *args)
##        self.condit = threading.Condition()

que = collections.deque

#game configuration
import bg_conf as conf

def summary(game_id=''):
    players = 'Depot |=> '+' => '.join(
        reversed(conf.roles[:conf.echelons]) )
    bline = '-'*len(players)
    w = ' ' * max(0,(50-len(players))//2)
    players = '''
{}+--{}--+
{}|  {}  |
{}+--{}--+'''.format(w, bline, w, players, w, bline)
    return '''
++  Welcome to the Beer Game {}!  ++
 
In this game, there are {} echelons/players:{}
The *external* Depot for the whole chain has *abundant*
supply. The following is true for all players:

1. Orders take {} week(s) to reach the supplier.
2. Shipment takes {} week(s) to reach the customer.
3. Inventory holding cost is {} per box per week,
4. and backlogging cost is {} per box per week.
5. The game lasts for {} weeks.

In the beginning, there are {} order(s) of {} boxes on
the way to the supplier, and {} shipment(s) of {} boxes each
on the way to the player. The initial inventory is {}.
'''.format(game_id, conf.echelons, players,
       conf.order_delay, conf.ship_delay,
       conf.holding_cost, conf.backlog_cost,
       len(conf.market_demands),

       conf.order_delay, conf.order_size, 
       conf.ship_delay, conf.order_size,           
       conf.init_inv)

def check_admin(passcode):
    return conf.password == passcode

class BeerGame:
    def __init__(self, games):
        self.make_pipeline()
        self.slots = [BGPlayer(i, self) for i in range(conf.echelons)]
        games.append(self)
        self.game_id = len(games)

    def make_pipeline(self):
        #player #i gets order from order_ques[i],
        #and puts order into order_ques[i+1]
        self.order_ques = [que(conf.order_size
                              for d in range(conf.order_delay))
                           for i in range(conf.echelons)]
        self.order_ques[0] = que(conf.market_demands)

        #player #i gets shipment from ship_ques[i+1]
        #and ships out to ship_ques[i]
        self.ship_ques = [que(conf.order_size
                              for d in range(conf.ship_delay))
                 for i in range(conf.echelons)]
        #the raw material depot
        loop = que(conf.order_size
                   for i in range(conf.ship_delay+conf.order_delay))
        self.order_ques.append(loop)
        self.ship_ques.append(loop)
        
        
    def enque(self, q, it): #producer
        #with q.condit:
            #q.append(it)
            #q.condit.notify()
        
        #using deque:
        q.append(it)
        
    def deque(self, q, real): #consumer
        #with q.condit:
            #q.condit.wait_for(lambda: len(q)>0)
            #it = q.pop(0)

        #using deque:
        it = (q.popleft() if real else q[0]
              ) if len(q)>0 else None
        return it
        
    def put_order(self, pid, boxes):
        q = self.order_ques[pid+1]
        self.enque(q, boxes)
        
    def get_order(self, pid, real=True):
        q = self.order_ques[pid]
        return self.deque(q, real)
    
    def ship_out(self, pid, boxes):
        q = self.ship_ques[pid]
        self.enque(q, boxes)
        
    def ship_in(self, pid, real=True):
        q = self.ship_ques[pid+1]
        return self.deque(q, real)

    def __repr__(self):
        return "BG-{}".format(self.game_id)

class BGPlayer:
    
    def __init__(self, pid, game):
        self.game = game
        self.pid = pid
        self.inv = conf.init_inv
        ordout = game.order_ques[pid+1]
        shipin = game.ship_ques[pid+1]
        self.wait = sum(ordout)
        if shipin is not ordout:
            self.wait += sum(shipin)
        self.cost = 0
        self.week = 0
        self.thread = None
        self.passcode = None

        #history and performance
        self.order_history = [] #placed orders
        self.inventory_history = []
        self.demand_history = []
        self.fulfill_history = []

        self.fulfilled_orders = 0 #orders directly fulfilled
        self.unfulfilled_orders = 0
        self.fulfilled_boxes = 0
        self.unfulfilled_boxes = 0
        self.backlogs = 0 #orders backloged
        self.onhands = 0
    
    def act(self, ask_order):
        wait, inv = self.wait, self.inv
        while True:
            shipin = self.game.ship_in(self.pid, False)
            if shipin is None: yield '''
Still WAITING for inbound shipment...
Your patience is much appreciated.'''
            else: break
                
        wait -= shipin

        backorder = max(0, -self.inv)
        fulfil = min(backorder, shipin)
        
        old_inv = inv
        inv += shipin
        
        yield (
'''
Event log of last week (week {}) in order of time:
========================================================

(1) Received a SHIPMENT of {} boxes. Thus your inventory
increased from {} to {} boxes, waiting for {} more boxes. 
'''.format(self.week, shipin, old_inv, inv, wait))

        #cost: demand came near the end of a week.
        cost = (inv * conf.holding_cost if inv>0
                      else - inv * conf.backlog_cost)


        while True:
            demand = self.game.get_order(self.pid, False)
            if demand is None: yield '''
Still WAITING for the order to arrive...
Your patience is much appreciated.'''
            else: break

        fulfilled_boxes = min(max(0, inv), demand)
            
        fulfil += fulfilled_boxes
            
        old_inv = inv
        inv -= demand
        
        #inv_pos = inv + wait
        yield (
'''
(2) The DEMAND for last week turned out to be {},
and you managed to SHIP {} boxes out.
Your inventory decreased to {} in the end.
The incurred cost is {} last week, total cost: {}.
'''.format(demand, fulfil, inv, cost, self.cost+cost))


        order = ask_order(self.week+1)
        wait += order
        yield (
"""
(3) Amount ordered: {}, now waiting for {} boxes."""
                     .format(order, wait))

        #commit to real changes:
        self.game.ship_in(self.pid)
        self.game.get_order(self.pid)
        self.game.ship_out(self.pid, fulfil)
        self.game.put_order(self.pid, order)
        self.wait, self.inv = wait, inv
        self.cost += cost
        self.week += 1 #increament
        
        self.order_history.append(order)
        self.demand_history.append(demand)
        self.fulfill_history.append(fulfil)
        self.inventory_history.append(old_inv)
        
        if old_inv <0: self.backlogs -= old_inv
        else: self.onhands += old_inv


        self.fulfilled_boxes += fulfilled_boxes
        self.unfulfilled_boxes += demand - fulfilled_boxes

        if demand == fulfilled_boxes:
            self.fulfilled_orders += 1 #orders directly fulfilled
        else:
            self.unfulfilled_orders += 1
        
        

    def __repr__(self):
        return "{}P{}".format(self.game, self.pid+1)
    
    def get_role(self):
        return conf.roles[self.pid]
    
    def save(self):
        filename = "BG-{}P{}.csv".format(self.game.game_id, self.pid+1)
        f=open(filename, 'wt')
        f.write("Game Report for {}\n".format(repr(self)))
        f.write('Total cost, {}\n'.format(self.cost))
        f.write('Fulfilled boxes, {}, Unfulfilled boxes, {}\n'.format(
            self.fulfilled_boxes, self.unfulfilled_boxes))
        f.write('Fulfilled orders, {}, Unfulfilled orders, {}\n'.format(
            self.fulfilled_orders, self.unfulfilled_orders))
        
        f.write('Total backlogs, {}, Total on-hands, {}\n'.format(
            self.backlogs, self.onhands))
        f.write('Week, Placed Order, Demand, Fulfill, Inventory\n')

        for w, (p, d, u, i) in enumerate(
            zip(self.order_history, self.demand_history,
                self.fulfill_history, self.inventory_history)):
            f.write('{},{},{},{},{}\n'.format(w+1,p,d,u,i))
        f.close()
        print("File saved:", filename)


enco = 'utf-8' #'ascii'

class ThreadedTCPRequestHandler(socketserver.BaseRequestHandler):
    games = collections.deque()
    glock = threading.Lock()   #to access games
    
    def setup(self):
        #from socketserver.StreamTCPHandler
        self.request.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, True)
        
        #self.request.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)

        #self.rfile = self.request.makefile('rb', -1)
        #self.wfile = self.request.makefile('wb', 0)

        self.thread = threading.current_thread()
        self.player = None
        
    def finish(self):
        if self.player != None:
            print('Player {} is released.'.format(self.player))
            self.player.thread = None
            self.player = None 
        self.thread = None
        
    def sendall(self, msg):
        self.request.sendall(bytes(msg, enco))
        #self.wfile.write(bytes(msg, enco))
        #try: self.wfile.flush()
        #except socket.error:
        #    print("FLUSH ERROR!")
        #else: print("MSG SENT!")
        #self.request.recv(8)
        if any(msg.startswith(h) for h in
               ('!ASK:', '!CODE:')):
            return
        #msg = str(self.rfile.readline().strip(), enco)
        msg = str(self.request.recv(128), enco)
        assert msg.startswith(':confirmed!')

    def ask_order(self, week):
        self.sendall('!ASK:Place your order for week {} here: '
                     .format(week))
        #make sure the entire number is received!
        data = str(self.request.recv(8), enco)
        return int(data)

    def login(self, code): #with glock.
        if code.startswith(':'): #any slot
            code = code[1:]
            for g in self.games:
                for p in g.slots:
                    if p.passcode is None:
                        p.passcode = code
                        self.player = p
                        p.thread = self.thread
                        break
                if self.player: break
            while self.player is None:
                g = BeerGame(self.games)
                for p in g.slots:
                    if p.passcode is None:
                        p.passcode = code
                        self.player = p
                        p.thread = self.thread
                        break
        else: #specific slot
            pid = code[:code.index(':')].upper()
            assert pid.startswith("BG-")
            code = code[len(pid)+1:]
            gid = int(pid[3:pid.index('P')])
            pid = int(pid[pid.index('P')+1: ])
            p = self.games[gid-1].slots[pid - 1]

            if p.passcode is None or code == p.passcode:
                self.player = p
                p.thread = self.thread
                p.passcode = code
            elif code.startswith('reset:'):
                #reset the players password by admin
                if check_admin(code[6:]):
                    p.passcode = None


    def handle(self):
        self.sendall("""!CODE:
        ++++++++++++++++++++++++++++++
        +    Your ID and PASSCODE    +
        ++++++++++++++++++++++++++++++

If you don't know your player ID (something like BG-1P2),
just skip your ID, you will be assigned an available ID
in the game, and the passcode your provided will be used
the next time you sign in.""")
        #code = 'BG-1P2:passcode' or ':passcode'
        code = str(self.request.recv(128), enco)
        with self.glock: self.login(code)
        if self.player is None:
            self.sendall("Can't find your player. Disconnecting...")
            return

        self.sendall(summary(self.player.game))

        self.sendall('''
********************************************************************
*  Welcome, you are the {} in the game {}.
*  Your player ID is {}. Please REMEMBER your ID and PASSCODE.
*  Weeks already played: {}.
*  Your inventory is {}.
*  You are waiting for {} boxes of ordered beer from the supplier.
********************************************************************
'''.format(self.player.get_role(), self.player.game,
           self.player, self.player.week, 
           self.player.inv, self.player.wait))
        
        while self.player.week < len(conf.market_demands):
            for msg in self.player.act(self.ask_order):
                self.sendall(msg)
                if self.player.thread is not self.thread:
                    return #lost the player
            #self.player.save() #for testing only

        self.player.save()

class ThreadedTCPServer(socketserver.TCPServer):
    
    def process_request(self, request, client_address):
        """Start a new thread to process the request."""
        print("Spawning by:", threading.current_thread().name)
        t = threading.Thread(target = self.process_request_thread,
                             args = (request, client_address))
                                                 
        t.daemon = self.daemon_threads
        t.start()

    # Decides how threads will act upon termination of the
    # main process
    daemon_threads = False

    def process_request_thread(self, request, client_address):
        """Same as in BaseServer but as a thread.

        In addition, exception handling is done here.
        """
        try:
            self.finish_request(request, client_address)
            self.shutdown_request(request)
        except:
            self.handle_error(request, client_address)
            self.shutdown_request(request)



def ask_int(msg, low=0, default=''):
    while True:
        i = input(msg).strip()
        if not i: i = str(default)
        
        try:
            n = int(i)
        except:
            print("ERROR: not an integer!")
            continue
        
        if n>=low: return i

        print("ERROR: integer < {}.".format(low))


if __name__ == "__main__":
    print(summary())
    server = ThreadedTCPServer((conf.host, conf.port),
                               ThreadedTCPRequestHandler)

    host, port = server.server_address
    print("Starting up server at {}:{}".format(host, port))
    
    server.serve_forever()

    #server.shutdown()
    #server.server_close()
    
    input("Server is down. Press <ENTER> to quit.")
