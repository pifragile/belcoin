from test import createtxns,createtxns2
from belcoin_node.util import wallet_genesis
BASE_PORT = 27870
BASE_PORT_RPC = 7080
BASE_PORT_GRPC = 50050

BLOCK_TIMEOUT = 1000000000 #in ticks
BLOCK_SIZE = 1 #in transactions

TIME_MULTIPLIER = 1000000000
TIMEOUT_CONST = 1000000000
TIMELOCK_CONST = 1000000000

REQUEST_TXN_TIMEOUT = 5


VERBOSE = True
VERBOSE_FAILURE = True
COINBASE = wallet_genesis