import random

from txjsonrpc.web import jsonrpc
from tesseract.util import b2hex
from tesseract.transaction import Transaction
from tesseract.serialize import SerializationBuffer
from tesseract.util import hex2b, hex_bytes_in_dict
from tesseract.address import address_to_pubkey
from belcoin_node.txnwrapper import TxnWrapper
from belcoin_node.config import VERBOSE, TIME_MULTIPLIER
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

        :param tx: Serialized Transaction in Hex format
        :return: 1 if transaction was put, 0 if txn was already there
        '''
        if self.node.storage.txns_received == 0:
            self.node.storage.time_measurement = time.time()
            self.node.storage.txns_received += 1
        t = hex2b(tx)

        tx = Transaction.unserialize(SerializationBuffer(t))

        if broadcast:
            if VERBOSE:
                print('Txn {} received.'.format(b2hex(
                    tx.txid)))
        else:
            if VERBOSE:
                print('Txn {} received from broadcast.'.format(b2hex(
                    tx.txid)))
        if self.node.storage.mempool[tx.txid] is None:
            self.node.storage.add_to_mempool(tx)
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


    def jsonrpc_puttxn_batch(self, txns, broadcast = True):

        """
        Used to receive and broadcast batches of transactions, should be used
        if big loads of transactions are sent

        :param txns: List of serialized transactions
        :param broadcast: True if the transactions should be broadcastetd
        :return: None
        """
        time.sleep(random.uniform(0, 1) * 0.5)
        if self.node.storage.txns_received == 0:
            self.node.storage.time_measurement = time.time()
            self.node.storage.txns_received += 1
        if broadcast:
            self.node.storage.broadcast_txn_batch(txns)
        for txn in txns:
            self.jsonrpc_puttxn(txn, broadcast = False)


    def jsonrpc_req_txn(self, txnid, addr):
        """
        Used to request a transaction from a node

        :param txnid: Transaction id in Hex format
        :param addr: String
        """
        time.sleep(random.uniform(0.08, 0.12))
        if VERBOSE:
            print('Received Request for txn {} from {}'.format(txnid, addr))
        if hex2b(txnid) in self.node.storage.invalid_txns:
            return None

        txn = self.node.storage.mempool[hex2b(txnid)]
        if txn is None:
            txnw = self.node.storage.db.get(hex2b(txnid))
            if txnw is None:
                txnw = self.node.storage.pend.get(hex2b(txnid))
            if txnw is None:
                if VERBOSE:
                    print('Transaction {} not found!'.format(txnid))
                return 0
            txn = TxnWrapper.unserialize(SerializationBuffer(txnw)).txn

        txn = b2hex(txn.serialize().get_bytes())
        return txn

    def jsonrpc_print_balances(self):
        self.node.storage.print_balances()

    def jsonrpc_getutxos(self, addresses):
        """
        Request all UTXOS for addresses
        :param addresses: List of addresses
        """
        utxos_by_addr = {}
        for address in addresses:
            pubkey = address_to_pubkey(address)
            utxo_refs = self.node.storage.utxos_for_pubkey(pubkey)
            utxos_by_addr[address] = [{
                'txid': b2hex(ref[0]),
                'index': ref[1],
                'blockheight': ref[2]
            } for ref in utxo_refs]
        return utxos_by_addr

    def jsonrpc_sendrawtx(self, txn, broadcast=True):
        """
        Same as puttxn
        :param txn: Serialized transaction in hex format
        :param broadcast: Bool
        """
        i = self.jsonrpc_puttxn(txn, broadcast)
        t = hex2b(txn)
        txid = Transaction.unserialize(SerializationBuffer(t)).txid
        if i == 1:
            return "Txn {} was put in mempool".format(str(txid))
        else:
            return "Txn {} was  already in mempool".format(str(txid))

    def jsonrpc_gettx(self, txid):
        """
        Used to get a transaction from th node
        :param txid: Transaction id in hex format
        :return:
        """
        txnw = self.node.storage.db.get(hex2b(txid))
        if txnw is None:
            return {}
        txnw = TxnWrapper.unserialize(SerializationBuffer(txnw))
        info = hex_bytes_in_dict(
            txnw.txn.to_dict())

        # Add blockheight
        info['blockheight'] = txnw.timestamp / TIME_MULTIPLIER
        return info

    def jsonrpc_getblockheight(self):
        return self.node.storage.current_time