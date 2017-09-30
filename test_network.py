from belcoin_node.node import Node
import os
from os.path import expanduser
import errno
import argparse
import shutil


BASE_PORT = 27870
BASE_PORT_RPC = 7080

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
for i in range(0, num_nodes):
    peers = list(addrs)
    del peers[i]
    peers_str = str(peers).replace(' ', '').replace('[','').replace(']',
                                                                    '').replace('\'','')
    print(peers_str)
    command = 'python belcoin_node/node.py {} {} {} {}'.format(i,
                                                            BASE_PORT_RPC+i,
                                                            addrs[i],
                                                            peers_str)
    os.system("gnome-terminal -e 'bash -l -c \""+command+"; exec bash\"'")