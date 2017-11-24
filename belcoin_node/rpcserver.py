from txjsonrpc.web import jsonrpc
from tesseract.util import b2hex
from tesseract.transaction import Transaction
from tesseract.serialize import SerializationBuffer
from tesseract.util import hex2b
from belcoin_node.txnwrapper import TxnWrapper
from belcoin_node.config import VERBOSE
import time

class RPCServer(jsonrpc.JSONRPC):
    def __init__(self, node):
        self.node = node
        super().__init__()

    def jsonrpc_set(self, key, val):
        self.node.storage.set(key, val)

    def jsonrpc_get(self, key):
        return self.node.storage.get(key)

    def jsonrpc_puttxn(self, tx, broadcast=True):
        '''

        :param tx:
        :return: 1 if transaction was put, 0 if txn was already there
        '''

        t = hex2b(tx)
        tx = Transaction.unserialize_full(SerializationBuffer(t))
        if broadcast:
            if VERBOSE:
                print('Txn {} received.'.format(b2hex(
                    tx.txid)))
        else:
            if VERBOSE:
                print('Txn {} received from broadcast.'.format(b2hex(
                    tx.txid)))

        if len([txn for txn in self.node.storage.mempool if txn[0] ==
                tx.txid]) == 0:
            self.node.storage.mempool.append((tx.txid, tx))
            if VERBOSE:
                print('Txn {} put in mempool.'.format(b2hex(
                    tx.txid)))
            rval = 1;
        else:
            if VERBOSE:
                print('Txn {} already in mempool.'.format(b2hex(
                    tx.txid)))
            rval = 0;

        if broadcast:
            if VERBOSE:
                print('Broadcasting transaction {}'.format(b2hex(
                    tx.txid)))
            self.node.storage.broadcast_txn(b2hex(t))
        return rval

    def jsonrpc_req_txn(self,txnid,addr):
        if VERBOSE:
            print('Received Request for txn {} from {}'.format(txnid, addr))
        if hex2b(txnid) in self.node.storage.invalid_txns:
            return None

        txn = [txn[1] for txn in self.node.storage.mempool if txn[0] ==
               hex2b(txnid)]
        if len(txn) > 0:
            txn = txn[0]
        else:
            txnw = self.node.storage.db.get(hex2b(txnid))
            if txnw is None:
                txnw = self.node.storage.pend.get(hex2b(txnid))
            if txnw is None:
                if VERBOSE:
                    print('Transaction {} not found!'.format(txnid))
                return 0
            txn = TxnWrapper.unserialize(SerializationBuffer(txnw)).txn

        txn = b2hex(txn.serialize_full().get_bytes())
        return txn

    def jsonrpc_print_balances(self):
        self.node.storage.print_balances()
