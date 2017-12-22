from test import createtxns,createtxns2
from belcoin_node.util import wallet_genesis
from tesseract.transaction import Transaction
from tesseract.serialize import SerializationBuffer
from tesseract.util import hex2b
import os
from os.path import expanduser

BASE_PORT = 27870
BASE_PORT_RPC = 7080
BASE_PORT_GRPC = 50050

BLOCK_TIMEOUT = 1000000000 #in ticks
BLOCK_SIZE = 10000 #in transactions

BATCH_SIZE = 10000

BACKOFF_AMOUNT = 300

LOOPING_CALL_TIME = 0.01

TIME_MULTIPLIER = 1000000000
TIMEOUT_CONST = 1000000000
TIMELOCK_CONST = 1000000000

REQUEST_TXN_TIMEOUT = 5

ADD_NETWORK_DELAY = True
NETWORK_DELAY_MIN = 0.02
NETWORK_DELAY_MAX = 0.05

VERBOSE = False
VERBOSE_FAILURE = False

#Coinbase is list of coinbase txns
#COINBASE = [wallet_genesis]
COINBASE = createtxns2.genesis_txn_list_batch()
#COINBASE = [createtxns.genesis_txn()]

#read 10000 test transactions from file
fileDir = os.path.dirname(os.path.realpath('__file__'))
f = open(expanduser('~/belcoin/test/txns_2.txt'), 'r')
content = f.readlines()
f.close()
content = [Transaction.unserialize(SerializationBuffer(hex2b(x.strip())))
           for x in content]

test_transactions = content
