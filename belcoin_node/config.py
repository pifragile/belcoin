from test import createtxns,createtxns2
from belcoin_node.util import wallet_genesis
from tesseract.transaction import Transaction
from tesseract.serialize import SerializationBuffer
from tesseract.util import hex2b
import os

BASE_PORT = 27870
BASE_PORT_RPC = 7080
BASE_PORT_GRPC = 50050

BLOCK_TIMEOUT = 1000000000 #in ticks
BLOCK_SIZE = 1000 #in transactions

TIME_MULTIPLIER = 1000000000
TIMEOUT_CONST = 1000000000
TIMELOCK_CONST = 1000000000

REQUEST_TXN_TIMEOUT = 5


VERBOSE = False
VERBOSE_FAILURE = False
#Coinbase is list of coinbase txns
#COINBASE = [wallet_genesis]
COINBASE = createtxns2.genesis_txn_list_batch()


fileDir = os.path.dirname(os.path.realpath('__file__'))
f = open('/home/pigu/belcoin/test/txns_1.txt', 'r')
content = f.readlines()
f.close()
content = [Transaction.unserialize(SerializationBuffer(hex2b(x.strip())))
           for x in content]
test_transactions = content