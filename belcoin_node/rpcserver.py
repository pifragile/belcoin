from txjsonrpc.web import jsonrpc
from tesseract.util import b2hex
from tesseract.transaction import Transaction
from tesseract.serialize import SerializationBuffer
from tesseract.util import hex2b
from belcoin_node.txnwrapper import TxnWrapper

class RPCServer(jsonrpc.JSONRPC):
    def __init__(self, node):
        self.node = node
        super().__init__()

    def jsonrpc_set(self, key, val):
        self.node.storage.set(key, val)

    def jsonrpc_get(self, key):
        return self.node.storage.get(key)

    def jsonrpc_puttxn(self, tx):
        t = hex2b(tx)
        tx = Transaction.unserialize_full(SerializationBuffer(t))

        if len([txn for txn in self.node.storage.mempool if txn[0] ==
                tx.txid]) == 0:
            self.node.storage.mempool.append((tx.txid, tx))
            print('Txn {} put in mempool on node {}.'.format(b2hex(
                tx.txid), self.node.nid))
        else:
            print('Txn {} already in mempool on node {}.'.format(b2hex(
                tx.txid), self.node.nid))
        print('broadcasting transaction {}...'.format(b2hex(tx.txid)))
        self.node.storage.broadcast_txn(b2hex(t))

    def jsonrpc_req_txn(self,txnid,addr):
        print('Received Request for block {} from {}'.format(txnid,addr))
        print('Sending...')
        txn = [txn[1] for txn in self.node.storage.mempool if txn[0] == txnid]
        if len(txn) > 0:
            txn = txn[0]
        else:
            txnw = self.node.storage.db.get(hex2b(txnid))
            if txnw is None:
                txn = None
            else:
                txn = TxnWrapper.unserialize(SerializationBuffer(txnw)).txn

        if txn is None:
            print('Transaction {} not found!'.format(b2hex(txnid)))
            return

        txn = b2hex(txn.serialize_full().get_bytes())
        return txn

