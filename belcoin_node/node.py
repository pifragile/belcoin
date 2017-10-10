from belcoin_node.storage import Storage
from belcoin_node.rpcserver import RPCServer
from twisted.web import server
from txjsonrpc.netstring import jsonrpc
from twisted.application import service, internet
from twisted.internet import reactor
import argparse
from threading import Thread



class Node(object):

    def __init__(self, self_address, partner_addrs, nid, peers_rpc):
        self.storage = Storage(self_address, partner_addrs, nid, self)
        self.nid = nid
        self.address = self_address
        self.partner_addrs = partner_addrs
        self.rpc_peers = dict(zip(partner_addrs, peers_rpc))#raft addr=>rpc addr

    def add_node(self, addr):
        self.storage.addNodeToCluster(addr, callback=cb)

def main():
    parser = argparse.ArgumentParser('Belcoin Node')
    parser.add_argument('id', type=int, help='Node ID')
    parser.add_argument('rpc_port', type=int,
                        help='Port where RPC Server should listen')
    parser.add_argument('rpc_peers',
                        help='Ports of the other nodes rpc ifaces')
    parser.add_argument('addr', help='Address for RAFT')
    parser.add_argument('peers', help='Address for RAFT')

    args = parser.parse_args()
    nid = args.id
    rpc_port = args.rpc_port
    addr = args.addr

    n = Node(addr, args.peers.split(','), nid, args.rpc_peers.split(','))

    #reactor.listenTCP(rpc_port, server.Site(RPCServer(n)))

    factory = jsonrpc.RPCFactory(RPCServer(n))
    reactor.listenTCP(rpc_port, factory)

    t = Thread(target=console,args=(n,nid,rpc_port,addr,))
    t.start()
    reactor.run()


def cb(err,a):
    print('Adding Node:' +str(a))

def console(n,nid,rpc_port,addr):
    print('Node {} listening for RPC messages on port {} and is connected to '
          'the consensus network with address {}'.format(nid,rpc_port,addr))
    print('Use \'add\' to add a node (not really working yet)')
    print('Use \'status\' to get node status)')
    while True:
        cmd = input('>>').split()
        if not cmd:
            continue
        elif cmd[0] == 'add':
            n.add_node(cmd[1])
        elif cmd[0] == 'status':
            print(n.storage.getStatus())
        else:
            continue
if __name__ == "__main__":
    main()
