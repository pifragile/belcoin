#!/usr/bin/python
import sys
from belcoin_node.node import Node
import time
import os
from os.path import expanduser
import errno
import argparse
import shutil
import gc


BASE_PORT = 27869

parser = argparse.ArgumentParser('Belcoin Node Tester')
parser.add_argument('num_nodes', type=int,
                    help='number of nodes to be started')
parser.add_argument('-e', '--erase_db', dest='erase', action='store_true')
args = parser.parse_args()
num_nodes = args.num_nodes

# if flag is set, erase all databases
if args.erase:
    shutil.rmtree(expanduser('~/.belcoin'))

#create directory for databases
try:
    os.makedirs(expanduser('~/.belcoin'))
except OSError as exc:
    if (exc.errno == errno.EEXIST and
            os.path.isdir(expanduser('~/.belcoin'))):
        pass
    else:
        raise

# create array with all adresses for the nodes
addrs = []
for i in range(0, num_nodes):
    addrs.append('localhost:' + str(BASE_PORT + i))

# create a list of all node objects
nodes = []
for i in range(0, num_nodes):
    peers = list(addrs)
    del peers[i]
    nodes.append(Node(addrs[i], peers, i))


#start testing console
print('Welcome to the testing console! Usage:')
print('>> set nodeid key value')
print('>> get nodeid key')
while True:
    cmd = input('>>').split()
    if not cmd:
        continue
    elif cmd[0] == 'set':
        addr = int(cmd[1])
        key = cmd[2]
        value = cmd[3]
        print ('###Sending (' + key + ',' + value + ') to '+ addrs[addr])
        time.sleep(0.5)
        nodes[int(cmd[1])].storage.set(cmd[2], cmd[3])
    elif cmd[0] == 'get':
        addr = int(cmd[1])
        key = cmd[2]
        print('###Requesting '+ key + ' from ' + addrs[addr])
        time.sleep(0.5)
        print(nodes[int(cmd[1])].storage.get(cmd[2]))
    elif cmd[0] == 'kill':
        addr = int(cmd[1])
        nodes[addr].storage.db.close()
        nodes[addr].storage.destroy()
        nodes[addr] = None
        gc.collect()
        time.sleep(0.5)
        print('###Killed node '+ str(addr))
    elif cmd[0] == 'wake':
        addr = int(cmd[1])
        if nodes[addr] is None:
            peers = list(addrs)
            del peers[addr]
            nodes[addr] = Node(addrs[addr], peers, addr)
            time.sleep(0.5)
            print('###Woke up '+ str(addr))
        else:
            time.sleep(0.5)
            print('###Node is already up '+ str(addr))
    else:
        continue