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
import random

host = 'localhost'
port = 8888

password = 'bgadmin' #password for admin

echelons = 2    # in [1,4]
order_delay = 1 # >= 1
ship_delay = 2  # >= 1
order_size = 5  # used before game starts
init_inv = 15   # initial inventory
holding_cost = 1 
backlog_cost = 2

market_demands = (5,)*5 + tuple(
    random.randint(8,10) for i in range(40))

roles = ["Retailer", "Distributor", "Bottler", "Brewer", "Depot"]

