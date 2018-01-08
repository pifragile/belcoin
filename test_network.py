from belcoin_node.node import Node
import os
from os.path import expanduser
import errno
import argparse
import shutil
from belcoin_node.config import BASE_PORT_RPC,BASE_PORT, BASE_PORT_GRPC

parser = argparse.ArgumentParser('Belcoin Node Tester')
parser.add_argument('num_nodes', type=int,
                    help='number of nodes to be started')
parser.add_argument('-e', '--erase_db', dest='erase', action='store_true')
args = parser.parse_args()
num_nodes = args.num_nodes

# if flag is set, erase all databases
try:
    if args.erase:
        shutil.rmtree(expanduser('~/.belcoin'))
except Exception:
    pass

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
addrs_rpc = []
for i in range(0, num_nodes):
    addrs.append('localhost:' + str(BASE_PORT + i))
    addrs_rpc.append('http://127.0.0.1:' + str(BASE_PORT_RPC + i))

# create a list of all node object
for i in range(0, num_nodes):
    peers = list(addrs)
    peers_rpc = list(addrs_rpc)
    del peers[i]
    del peers_rpc[i]

    peers_str = ",".join(peers)
    peers_rpc_str = ",".join(peers_rpc)
    #print(peers_str)
    command = 'python belcoin_node/node.py {} {} {} {} {} {}'.format(i,
                                                            BASE_PORT_RPC+i,
                                                            peers_rpc_str,
                                                            addrs[i],
                                                            peers_str,
                                                            BASE_PORT_GRPC+i) +\
                                                            " &>> output/0.txt"
    print(command)
    # os.system("gnome-terminal -e 'bash -l -c \""+command+"; exec bash\"'")