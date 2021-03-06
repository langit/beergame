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


import sys
version = sys.version_info
if version.major < 3: 
    input = raw_input
    def bytes(x,y): return x
    str_sys = str
    def str(x,y=None): return str_sys(x)
import socket
import collections
from getpass import getpass

port = 8888 #this must agree with bg_config.port

enco = 'utf-8'

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

def client(ip, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((ip, port))
    
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, True)
    #rfile = sock.makefile('rb', -1)


    confirmed = bytes(':confirmed!',enco)
    
    try:
        while True:
            #msg = str(rfile.readline(), enco)
            msg = str(sock.recv(1024),enco)
            if msg.startswith('!CMD:'):
                while True:
                    cmd = input(msg[5:])
                    if cmd: break
                sock.sendall(bytes(cmd, enco))
            elif msg.startswith('!CODE:'):
                print(msg[6:])
                user = 'admin'
                word = getpass("Admin password: ")
                sock.sendall(bytes(user+":"+word, enco))
            elif msg.startswith('!END:'):
                print(msg[5:]) #end of session
                break
            else:
                print(msg)
                input("Press <ENTER> to continue...")
                sock.sendall(confirmed)
    finally:
        #rfile.close()
        sock.close()
        input("Your session ended. Press <ENTER> to quit.")


if __name__ == "__main__":

    host = input("Beer Game Host: ")
    if not host: host = 'localhost'
    #port = int(ask_int("A four digit port [8888]: ", 1000, 8888))
    
    client(host, port)
