#!/usr/bin/python
import sys
from belcoin_node.node import Node


BASE_PORT = 27869


if len(sys.argv) < 2:
    print('Usage: Please provide the number of nodes you want to start')
    sys.exit(-1)

num_nodes = int(sys.argv[1])

addrs = []
for i in range(0,num_nodes):
    addrs.append('localhost:' + str(BASE_PORT+i))

nodes = []
for i in range(0, num_nodes):
    peers = list(addrs)
    del peers[i]
    nodes.append(Node(addrs[i], peers))

print('Welcome to the testing console! Usage:')
print('>> set nodeid key value')
print('>> get nodeid key')
while True:
    cmd = input('>>').split()
    if not cmd:
        continue
    elif cmd[0] == 'set':
        nodes[int(cmd[1])].storage.set(cmd[2],cmd[3])
    elif cmd[0] == 'get':
        print(nodes[int(cmd[1])].storage.get(cmd[2]))
    else:
        continue