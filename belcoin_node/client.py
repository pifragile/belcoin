from twisted.internet import reactor
from txjsonrpc.web.jsonrpc import Proxy
from tesseract.transaction import Transaction
from tesseract.util import b2hex
import argparse

# parser = argparse.ArgumentParser('Belcoin Client')
# parser.add_argument('port', type=int,
#                     help='port to send to on localhost')
# args = parser.parse_args()
# port = args.port



def printValue(value):
    print ("Result: %s" % str(value))

def printError(error):
    print ('error', error)

def cont(data):
    run()

def call_set(port,key,value):
    proxy = Proxy('http://127.0.0.1:'+str(port)+'/')
    #proxy = Proxy('127.0.0.1', port)
    d = proxy.callRemote('set', key, value)
    d.addCallback(printValue).addErrback(printError).addBoth(cont)

def call_get(port,key):
    proxy = Proxy('http://127.0.0.1:' + str(port) + '/')
    #proxy = Proxy('127.0.0.1', port)
    d = proxy.callRemote('get', key)
    d.addCallbacks(printValue, printError).addBoth(cont)

def call_txn(port,txn):
    proxy = Proxy('http://127.0.0.1:' + str(port) + '/')
    #proxy = Proxy('127.0.0.1', port)
    d = proxy.callRemote('puttxn', txn, True)
    d.addCallbacks(printValue, printError).addBoth(cont)

def run():
        cmd = input('>>').split()
        if not cmd:
            run()
        elif cmd[0] == 'set':
            port = int(cmd[1])
            key = cmd[2]
            value = cmd[3]
            print('###Sending (' + key + ',' + value + ') to '+ '127.0.0.1:'+str(port)+'/')
            reactor.callLater(0,call_set,port,key,value)

        elif cmd[0] == 'get':
            port = int(cmd[1])
            key = cmd[2]
            print('###Requesting '+ key + ' from ' + '127.0.0.1:'+str(port)+'/')
            reactor.callLater(0, call_get, port, key)

        elif cmd[0] == 'txn':
            port = int(cmd[1])
            print('###Sending test transaction to ' + '127.0.0.1:'+str(
                port)+'/')
            txn = b2hex(Transaction([],[]).serialize_full().get_bytes())
            reactor.callLater(0, call_txn, port, txn)

        else:
            run()

print('This is the client! Usage:')
print('>> set port key value')
print('>> get port key')
reactor.callWhenRunning(run)
reactor.run()