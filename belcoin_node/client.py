from twisted.internet import reactor
from txjsonrpc.web.jsonrpc import Proxy
from tesseract.transaction import Transaction
from tesseract.util import b2hex
from test import createtxns
from belcoin_node.config import BASE_PORT_RPC
from random import randint
import time
import argparse

# parser = argparse.ArgumentParser('Belcoin Client')
# parser.add_argument('port', type=int,
#                     help='port to send to on localhost')
# args = parser.parse_args()
# port = args.port
k = 0
b = 0
test_transactions = createtxns.generate_htlc_txns() + \
                    createtxns.generate_htlc_txns2()
                    #createtxns.generate_partial_txns()
                    # createtxns.generate_txns()+ \
                    #createtxns.generate_conflicting_txns() + \
                    #createtxns.generate_unbalaced_txn()

num_txns = 0
num_bal = 0



def printValue(value):
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
    print('###Sending test transaction to ' + '127.0.0.1:' + str(
        port) + '/')

    d = proxy.callRemote('puttxn', txn, True)
    d.addCallbacks(printValue, printError).addBoth(cont_txn)
    #test_txns()

def call_bal(port):
    try:
        proxy = Proxy('http://127.0.0.1:' + str(port) + '/')
        print('###Send request to print balances to ' + '127.0.0.1:' + str(
        port) + '/')

        d = proxy.callRemote('print_balances')
        d.addCallbacks(printValue, printError).addBoth(cont_bal)
        print_balances()
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
            txn = b2hex(Transaction([],[]).serialize_full().get_bytes())
            reactor.callLater(0, call_txn, port, txn)

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
        txn = test_transactions[k]
        reactor.callLater(0, call_txn, BASE_PORT_RPC + randint(0, 3),
                          b2hex(txn.serialize_full().get_bytes()))
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