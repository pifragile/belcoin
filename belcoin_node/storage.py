from pysyncobjbc import SyncObj, SyncObjConf, replicated
import plyvel
from os.path import join, expanduser
from tesseract.serialize import SerializationBuffer
import time
from tesseract.transaction import Transaction
from tesseract.util import b2hex,hex2b
from tesseract.exceptions import InvalidTransactionError
from tesseract.crypto import verify_sig, NO_HASH
from pysyncobjbc.syncobj import BLOCK_SIZE
from belcoin_node.txnwrapper import TxnWrapper
from twisted.internet import reactor
from txjsonrpc.netstring.jsonrpc import Proxy

class Storage(SyncObj):
    def __init__(self, self_addr, partner_addrs, nid, node):
        cfg = SyncObjConf(dynamicMembershipChange=True)
        super(Storage, self).__init__(self_addr, partner_addrs, cfg)
        self.addr = self_addr
        self.nid = nid
        self.bcnode = node
        self.num_missing_txns = 0
        self.num_received_txns = 0


        self.db = plyvel.DB(join(expanduser('~/.belcoin'), 'db_'+str(nid)),
                            create_if_missing=True)

    @replicated
    def set(self, key, value):
        print('Node ' +str(self.nid) + ' received ('+key+','+value+') for storage')
        self.db.put(bytes(key, 'utf-8'), bytes(value, 'utf-8'))

    # def get(self, key):
    #     print('Node ' +str(self.nid)+ ' received a request for '+key)
    #     val = self.db.get(bytes(key, 'utf-8'))
    #     if val is None:
    #         return '###NOT FOUND###'
    #     else:
    #         return self.db.get(bytes(key, 'utf-8')).decode()

    def get(self, key, default=None):
        """Get an object from storage in a dictionary-like way."""
        assert isinstance(key, bytes)
        val = self.db.get(key)

        if val is None:
            return default

        return TxnWrapper.unserialize(SerializationBuffer(val))

    def broadcast_txn(self, txn):
        if not reactor.running:
            reactor.callWhenRunning(self.broadcast_txn, txn)
            reactor.run()
        else:
            for addr in list(self.bcnode.rpc_peers.values()):
                reactor.callLater(0, self.send_txn,addr,txn)

    def send_block(self):
        txns = self.mempool[:BLOCK_SIZE]
        block = [item[0] for item in txns]
        self.processing = True
        self.find_missing_transactions(block)

    @replicated
    def start(self, block):
        self.check_block(block)
        # TODO wait until process_block returns.. notify???

    def check_block(self, block):
        self.processing = True
        self.current_block = list(block)
        wait = False
        # TODO optimize: only the txns that were not found need to be checked
        for txid in block:
            tx = [txn for txn in self.mempool if txn[0] == txid]
            if len(tx) == 0:
                wait = True
                self.request_txn(txid)
                time.sleep(0.5)
        if not wait:
            self.process_block(block)


    @replicated
    def find_missing_transactions(self,block):
        self.current_block = block
        missing_txns = []
        for txid in block:
            tx = [txn for txn in self.mempool if txn[0] == txid]
            if len(tx) == 0:
                missing_txns.append(txid)
        if len(missing_txns) > 0:
            if not reactor.running:
                reactor.callWhenRunning(self.request_missing_transactions,
                                        missing_txns)
                reactor.run()
            else:
                self.request_missing_transactions(missing_txns)
        else:
            self.process_block(block)

    def transaction_received(self, value):
        tx = Transaction.unserialize_full(SerializationBuffer(hex2b(value)))
        print('node {} received txn {}'.format(self.nid,
                                               b2hex(tx.txid)))

        if len([txn for txn in self.mempool if txn[0] ==
                tx.txid]) == 0:
            self.mempool.append((tx.txid, tx))
            print('Txn {} put in mempool on node {}.'.format(b2hex(
                tx.txid), self.nid))
        else:
            print('Txn {} already in mempool on node {}.'.format(
                b2hex(tx.txid), self.nid))

        self.num_received_txns += 1
        if self.num_received_txns == self.num_received_txns:
            self.process_block(self.current_block)

    def transaction_receive_error(self, error):
        pass
        # TODO re request txn on failure

    def request_missing_transactions(self, missing_txns):
        for txn in missing_txns:
            reactor.callLater(0, self.request_missing_transaction,txn)

    def request_missing_transaction(self, txnid):
        print('requesting transaction {} from leader'.format(b2hex(txnid)))
        proxy = Proxy(self.bcnode.rpc_peers[self._getLeader()])
        d = proxy.callRemote('req_txn', b2hex(txnid), self.addr)
        d.addCallbacks(self.transaction_received,
                       self.transaction_receive_error)

    def transaction_sent(self, value):
        pass #value = 1 if txn was written, 0 if it already existed

    def transaction_send_error(self,error):
        # TODO maybe resend txn
        print(error)

    def send_txn(self, addr, txn):
        print('Sending txn to {}'.format(addr))
        addr = addr.split(':')
        proxy = Proxy(addr[0], int(addr[1]))
        d = proxy.callRemote('puttxn', txn, False)
        d.addCallbacks(self.transaction_sent,
                       self.transaction_send_error)

    def process_block(self, block):

        for txid in block:
            tx = [txn[1] for txn in self.mempool if txn[0] == txid]

            if len(tx) == 0:
                raise InvalidTransactionError(
                    "VERY STRANGE ERROR".format(self.nid))
            if len(tx) > 1:
                raise InvalidTransactionError(
                    "COLLISION OOOHHH MYYYY GOOOOD".format(self.nid))
            txn = tx[0]
            addr = self.addr
            ########################
            # verify and write txn #
            ########################
            ts = int(time.time() * 1000000000)
            for inp in txn.inputs:
                if inp.txid == NO_HASH:  # skip dummy inputs
                    continue
                try:
                    output_txnw = self[inp.txid]
                    spent_output = output_txnw.txn.outputs[inp.index]
                except KeyError:
                    if addr == self.addr:
                        print("Invalid input on transaction %s!" % b2hex(
                            txn.txid))

                    raise InvalidTransactionError(
                        "Invalid input on transaction %s!" % b2hex(txn.txid))

                # verify signatures
                if (not verify_sig(txn.txid, spent_output.pubkey,
                                   inp.signature) or
                        not verify_sig(txn.txid, spent_output.pubkey2,
                                       inp.signature2)):
                    if addr == self.addr:
                        print("Invalid signatures on transaction %s!" % b2hex(
                            txn.txid))

                    raise InvalidTransactionError(
                        "Invalid signatures on transaction %s!" % b2hex(
                            txn.txid))

                # check if outputs are unspent
                if not output_txnw.utxos[inp.index]:
                    if addr == self.addr:
                        print( "Transactions %s uses spent outputs!" % b2hex(
                            txn.txid))
                    raise InvalidTransactionError(
                        "Transactions %s uses spent outputs!" % b2hex(
                            txn.txid))

            # set all outputs to spent
            for inp in txn.inputs:
                output_txnw = self[inp.txid]
                output_txnw.utxos[inp.index] = False
                self[inp.txid] = output_txnw

            # write txn to db
            self[txn.txid] = TxnWrapper(txn, ts)
            print('txn {} ACCEPTED\n'.format(b2hex(txid)))
            self.mempool = [txn for txn in self.mempool if txn[0] != txid]
            self.processing = False






    def __getitem__(self, key):
        obj = self.get(key)
        if obj is None:
            raise KeyError('Key %s not found.' % (b2hex(key)))
        return obj

    def __setitem__(self, key, obj):
        assert isinstance(key, bytes)

        self.db.put(key, obj.serialize().get_bytes())

    def __contains__(self, key):
        return self.db.get(key) is not None