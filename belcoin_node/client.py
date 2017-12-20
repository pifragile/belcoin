from twisted.internet import reactor
from txjsonrpc.web.jsonrpc import Proxy
from tesseract.transaction import Transaction
from tesseract.util import b2hex
from tesseract.address import pubkey_to_address
from test import createtxns,createtxns2
from belcoin_node.config import BASE_PORT_RPC, VERBOSE, BATCH_SIZE
from belcoin_node.util import PUBS
from random import randint
import time
import argparse
from belcoin_node.config import test_transactions

# parser = argparse.ArgumentParser('Belcoin Client')
# parser.add_argument('port', type=int,
#                     help='port to send to on localhost')
# args = parser.parse_args()
# port = args.port
k = 0
b = 0
# test_transactions = createtxns2.generate_txns_batch()
#                     #createtxns.generate_txns()
#                     #createtxns.generate_pending_txns() +\
#                     #createtxns.generate_pending_txns2() #"+ \
#                     #createtxns2.generate_many_txns2()
#                     #createtxns2.generate_txns() +\
#                     #createtxns2.generate_many_txns()
#                     # createtxns2.generate_txns() + \
#                     #createtxns2.generate_many_txns() #+ \
#                     #createtxns2.generate_txns2()
#                     # createtxns.generate_htlc_txns() + \
# #                   createtxns.generate_htlc_txns2()
#                     #createtxns.generate_txns()
#                     #createtxns.generate_pending_txns() +\
#                     #createtxns.generate_conflicting_txn_pend()
#                     # createtxns.generate_pending_txns2()
#                     #createtxns.generate_partial_txns()
#                     # createtxns.generate_txns()+ \
#                     #createtxns.generate_conflicting_txns() + \
#                     #createtxns.generate_unbalaced_txn()

num_txns = 0
num_bal = 0





def printValue(value):
    if VERBOSE:
        print("Result: %s" % str(value))


def printError(error):
    print ('error', error)


def cont_txn_batch(data):
    global num_txns
    num_txns += BATCH_SIZE
    if num_txns == len(test_transactions):
        reactor.stop()
    else:
        test_txns_batch()


def call_txn_batch(port,txns):
    proxy = Proxy('http://127.0.0.1:' + str(port) + '/')
    if VERBOSE:
        print('###Sending test transaction to ' + '127.0.0.1:' + str(
            port) + '/')

    d = proxy.callRemote('puttxn_batch', txns)
    d.addCallbacks(printValue, printError)
    d.addBoth(cont_txn_batch)
    test_txns_batch()


def test_txns_batch():
    global k
    if k < len(test_transactions):
        if k % BATCH_SIZE == 0:
            txns = test_transactions[k:k+BATCH_SIZE]
            txns = [b2hex(txn.serialize().get_bytes()) for txn in txns]
            reactor.callLater(0, call_txn_batch, BASE_PORT_RPC + randint(0, 3), txns)
            k += BATCH_SIZE


reactor.callWhenRunning(test_txns_batch)
reactor.run()