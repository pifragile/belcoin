from twisted.internet import reactor
from txjsonrpc.web.jsonrpc import Proxy
from tesseract.transaction import Transaction
from tesseract.util import b2hex
from tesseract.address import pubkey_to_address
from test import createtxns,createtxns2
from belcoin_node.config import BASE_PORT_RPC, VERBOSE
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

def cont_txn(data):
    global num_txns
    num_txns += 1
    if num_txns == len(test_transactions):
        run()
    else:
        test_txns()

def cont_bal(data):
    try:
        global num_bal
        num_bal += 1
        if num_bal == 4:
            run()
        else:
            print_balances()
    except Exception as err:
        print(err)



def call_txn(port,txn):
    proxy = Proxy('http://127.0.0.1:' + str(port) + '/')
    if VERBOSE:
        print('###Sending test transaction to ' + '127.0.0.1:' + str(
            port) + '/')

    d = proxy.callRemote('sendrawtx', txn, True)
    d.addCallbacks(printValue, printError)
    d.addBoth(cont_txn)
    # test_txns()

def call_bal(port):
    try:
        proxy = Proxy('http://127.0.0.1:' + str(port) + '/')
        if VERBOSE:
            print('###Send request to print balances to ' + '127.0.0.1:' + str(
            port) + '/')

        d = proxy.callRemote('print_balances')
        d.addCallbacks(printValue, printError).addBoth(cont_bal)
        print_balances()
    except Exception as err:
        print(err)

def call_utxos(port, addr):
    try:
        proxy = Proxy('http://127.0.0.1:' + str(port) + '/')
        if VERBOSE:
            print('###Send utxo request to ' + '127.0.0.1:' + str(
            port) + '/')

        d = proxy.callRemote('getutxos', [addr])
        d.addCallbacks(printValue, printError)
    except Exception as err:
        print(err)

def call_gettx(port, txid):
    try:
        proxy = Proxy('http://127.0.0.1:' + str(port) + '/')
        if VERBOSE:
            print('###Send gettx request ' + '127.0.0.1:' + str(
            port) + '/')

        d = proxy.callRemote('gettx', txid)
        d.addCallbacks(printValue, printError)
    except Exception as err:
        print(err)

def run():
        cmd = input('>>').split()
        if not cmd:
            run()

        elif cmd[0] == 'bal':
            try:
                global b
                global num_bal
                num_bal = 0
                b = 0
                print_balances()
            except Exception as err:
                print(err)

        elif cmd[0] == 'txn':
            port = int(cmd[1])
            print('###Sending test transaction to ' + '127.0.0.1:'+str(
                port)+'/')
            txn = b2hex(Transaction([],[]).serialize().get_bytes())
            reactor.callLater(0, call_txn, port, txn)

        elif cmd[0] == 'utxos':
            port = int(cmd[1])
            reactor.callLater(0, call_utxos, port, pubkey_to_address(PUBS[
                                                                        int(
                                                                             cmd[
                                                                             2])]))
        elif cmd[0] == "gettx":
            reactor.callLater(0, call_gettx, int(cmd[1]), cmd[2])

        elif cmd[0] == 'txns':
            global num_txns
            global k
            num_txns = 0
            k = 0
            try:
                test_txns()
            except Exception as err:
                print(err)
        else:
            run()

def test_txns():
    global k
    if k < len(test_transactions):
        # if (k % 5) == 0 and k > 0:
        #     time.sleep(10)
        #time.sleep(0.1)
        txn = test_transactions[k]
        reactor.callLater(0, call_txn, BASE_PORT_RPC + randint(0, 3),
                          b2hex(txn.serialize().get_bytes()))
        k +=1

def print_balances():
    global b
    if b < 4:
        reactor.callLater(0, call_bal, BASE_PORT_RPC + b)
        b += 1

print('This is the client! Usage:')
print('>> set port key value')
print('>> get port key')
reactor.callWhenRunning(run)
reactor.run()