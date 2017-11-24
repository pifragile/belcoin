from txjsonrpc.web import jsonrpc
from tesseract.util import b2hex
from tesseract.transaction import Transaction
from tesseract.serialize import SerializationBuffer
from tesseract.util import hex2b
from belcoin_node.txnwrapper import TxnWrapper
from belcoin_node.config import VERBOSE, BLOCK_SIZE
import time

class RPCServer(jsonrpc.JSONRPC):
    def __init__(self, node):
        self.node = node
        super().__init__()

    def jsonrpc_set(self, key, val):
        self.node.storage.set(key, val)

    def jsonrpc_get(self, key):
        return self.node.storage.get(key)

    def jsonrpc_puttxn(self, tx):
        '''

        :param tx:
        :return: 1 if transaction was put, 0 if txn was already there
        '''
        t = hex2b(tx)
        tx = Transaction.unserialize_full(SerializationBuffer(t))
        if VERBOSE:
            print('Txn {} received.'.format(b2hex(
                tx.txid)))
        if len([txn for txn in self.node.storage.mempool if txn[0] ==
                tx.txid]) == 0:
            self.node.storage.mempool.append((tx.txid, tx))
            if VERBOSE:
                print('Txn {} put in mempool.'.format(b2hex(
                    tx.txid)))
            self.node.storage.try_process()
            rval = 1
        else:
            if VERBOSE:
                print('Txn {} already in mempool.'.format(b2hex(
                    tx.txid)))
            rval = 0

        return rval

    def jsonrpc_print_balances(self):
        self.node.storage.print_balances()
