from belcoin_node.storage import Storage
from belcoin_node.rpcserver import RPCServer
from twisted.web import server
from twisted.internet import reactor
import argparse
from threading import Thread


class Node(object):

    def __init__(self, self_address, partner_addrs, nid):
        self.storage = Storage(self_address, partner_addrs, nid)
        self.nid = nid

    def add_node(self, addr):
        self.storage.addNodeToCluster(addr)


def main():
    parser = argparse.ArgumentParser('Belcoin Node')
    parser.add_argument('id', type=int, help='Node ID')
    parser.add_argument('rpc_port', type=int,
                        help='Port where RPC Server should listen')
    parser.add_argument('addr', help='Address for RAFT')

    args = parser.parse_args()
    nid = args.id
    rpc_port = args.rpc_port
    addr = args.addr

    n = Node(addr, [], nid)
    reactor.listenTCP(rpc_port, server.Site(RPCServer(n)))
    t = Thread(target=console,args=(n,))
    t.start()
    reactor.run()

def console(n):
    while True:
        cmd = input('>>').split()
        if not cmd:
            continue
        elif cmd[0] == 'add':
            n.add_node(cmd[1])
            print('huhu')
        else:
            continue
if __name__ == "__main__":
    main()
