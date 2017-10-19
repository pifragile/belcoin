import time
import requests
import json
import plyvel
from os.path import join, expanduser
from belcoin_node.txnwrapper import TxnWrapper
from belcoin_node.util import PUBS
from belcoin_node.pendingdb import PendingDB
from tesseract.serialize import SerializationBuffer
from tesseract.transaction import Transaction,Input
from tesseract.util import b2hex, hex2b
from tesseract.exceptions import InvalidTransactionError
from tesseract.crypto import verify_sig, NO_HASH, merkle_root, sha256
from pysyncobjbc import SyncObj, SyncObjConf, replicated
from belcoin_node.config import BLOCK_SIZE, TIME_MULTIPLIER, TIMEOUT_CONST, TIMELOCK_CONST
from twisted.internet import reactor
from txjsonrpc.web.jsonrpc import Proxy
from terminaltables import AsciiTable

from test import createtxns


class Storage(SyncObj):
    def __init__(self, self_addr, partner_addrs, nid, node):
        cfg = SyncObjConf(dynamicMembershipChange=True)
        super(Storage, self).__init__(self_addr, partner_addrs, cfg)
        self.addr = self_addr
        self.nid = nid
        self.bcnode = node
        self.db = plyvel.DB(join(expanduser('~/.belcoin'), 'db_'+str(nid)),
                            create_if_missing=True)
        self.pend = PendingDB(nid) #db of txns that have a timelock to wait


        #create genesis transaction:
        gentxn = createtxns.genesis_txn()
        if not gentxn.txid in self:
            self[gentxn.txid] = TxnWrapper(
                gentxn, 0)

        #create index pubkey ==> (txid, index)
        self.pub_outs = {}
        for txid, txnw in self.db:
            txnw = TxnWrapper.unserialize(SerializationBuffer(txnw))
            txn = txnw.txn
            self.add_txn_to_balance_index(txn, self.pub_outs)

        #create index pubkey ==> (txid, index) for pending txns
        self.pub_outs_pend = {}
        for txid, txnw in self.pend.db:
            txnw = TxnWrapper.unserialize(SerializationBuffer(txnw))
            txn = txnw.txn
            self.add_txn_to_balance_index(txn, self.pub_outs_pend)


    def add_txn_to_balance_index(self, txn, index):
        txid = txn.txid
        for i in range(len(txn.outputs)):
            o = txn.outputs[i]
            for p in o.get_pubkeys():
                if p in index:
                        index[p].add((txid, i))
                else:
                    index[p] = set([(txid, i)])

    def del_out_from_balance_index(self, pubkeys, txid, i, index):
        index_name = "pub_outs" if index == self.pub_outs else "pub_outs_pend"
        for pubkey in pubkeys:
            if pubkey not in index:
                print('trying to delete output for a pubkey which doesn\'t '
                      'exist from ' + index_name)
                continue

            try:
                index[pubkey].remove((txid, i))
            except KeyError:
                print('trying to delete output which doesn\'t exist from '+
                      index_name)
                continue

    def get_balance(self, pubkey, index):
        bal = 0
        bal_partial = 0
        bal_htlc = 0

        if pubkey not in index:
            return [0, 0, 0]

        for (txid, i) in index[pubkey]:

            txnw = self[txid] if index == self.pub_outs else self.pend[txid]

            o = txnw.txn.outputs[i]
            #Case timeout reached
            if pubkey in [o.pubkey, o.pubkey2] and time.time() * \
                    TIME_MULTIPLIER - txnw.timestamp >= o.htlc_timeout * TIMEOUT_CONST:
                if o.pubkey == o.pubkey2:
                    bal += o.amount
                else:
                    bal_partial += o.amount

            if pubkey == o.htlc_pubkey and time.time() * \
                    TIME_MULTIPLIER - txnw.timestamp < o.htlc_timeout * TIMEOUT_CONST:
                bal_htlc += o.amount

        return [bal, bal_partial, bal_htlc]

    def print_balances(self):
        print('Balances: ')
        table_data = [
            ['Owner','Totally owned', 'Partially owned', 'HTLC (if secret '
                                                      'can ' \
                                                    'be '
                                                 'provided)']]
        for i in range(len(PUBS)):
            table_data.append([i] + self.get_balance(PUBS[i],self.pub_outs))
        table = AsciiTable(table_data)
        print(table.table)

        print('Balances (pending): ')
        table_data = [
            ['Owner','Totally owned', 'Partially owned', 'HTLC (if secret '
                                                      'can ' \
                                                    'be '
                                                 'provided)']]
        for i in range(len(PUBS)):
            table_data.append([i] + self.get_balance(PUBS[i],
                                                     self.pub_outs_pend))
        table = AsciiTable(table_data)
        print(table.table)

    def check_pend_replacement(self, txn):
        """
        Returns (x,y)
        x is True if the txn can be put into pend, be written to the db
        respectively
        y is true if a matching txn was found in pend

        Assumption: For a txn to be able to replace another one the inputs
        have to match exactly.
        """
        for txid, txnw in self.pend.db:
            txnw = TxnWrapper.unserialize(SerializationBuffer(txnw))
            tx = txnw.txn

            if set([str(inp) for inp in map(self.comparable_input,
                                               tx.inputs)])\
                == set([str(inp) for inp in map(self.comparable_input,
                                               txn.inputs)]):
                if time.time() * TIME_MULTIPLIER - txnw.timestamp > tx.timelock * \
                        TIMELOCK_CONST:
                    return False, True
                if txn.seq <= tx.seq:
                    return False, True
                self.del_from_pending(tx)
                return True, True
        return True, False


    def comparable_input(self, inp):
        return {
            'txid': b2hex(inp.txid),
            'index': inp.index,
            # 'signature': b2hex(inp.signature),
            # 'signature2': b2hex(inp.signature2),
            # 'htlc_preimage': b2hex(inp.htlc_preimage)
        }



    @replicated
    def update_pend(self):
        for txid, txnw in self.pend.db:
            txnw = TxnWrapper.unserialize(SerializationBuffer(txnw))
            timestamp = txnw.timestamp
            timelock = txnw.txn.timelock
            if time.time() * TIME_MULTIPLIER - timestamp > timelock * \
                        TIMELOCK_CONST:

                self.del_from_pending(txnw.txn)
                if self.verify_txn(txnw.txn, check_pend=False):
                    self.write_txn_to_db(txnw.txn, timestamp)
                    print('Transaction {} was pending and now put in '
                          'db'.format(b2hex(txid)))
                else:
                    print('Transaction {} was pending and could not be '
                          'written to db, see reason above'.format(b2hex(
                          txid)))

    def del_from_pending(self, tx):
        del self.pend[tx.txid]
        for i in range(len(tx.outputs)):
            self.del_out_from_balance_index(tx.outputs[
                                                i].get_pubkeys(),
                                            tx.txid, i,
                                            self.pub_outs_pend)


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
            for addr in list(self.bcnode.rpc_peers.values()):#[:2]:
                reactor.callLater(0, self.send_txn, addr, txn)

    def send_block(self):
        txns = self.mempool[:BLOCK_SIZE]
        block = [item[0] for item in txns]
        self.processing = True
        self.find_missing_transactions(block)

    @replicated
    def find_missing_transactions(self, block):
        print('received block {}'.format(b2hex(merkle_root(block))))
        self.current_block = block
        missing_txns = []
        for txid in block:
            tx = [txn for txn in self.mempool if txn[0] == txid]
            if len(tx) == 0:
                missing_txns.append(txid)
        if len(missing_txns) > 0:
                self.request_missing_transactions(missing_txns)
        else:
            self.process_block(block)

    def request_missing_transactions(self, missing_txns):
        for txn in missing_txns:
            self.request_missing_transaction(txn)
        self.process_block(self.current_block)

    def request_missing_transaction(self, txnid):
        # TODO retry if leader is down
        print('requesting transaction {} from leader'.format(b2hex(txnid)))
        addr = self.bcnode.rpc_peers[self._getLeader()]

        payload = {
            "method": "req_txn",
            "params": [b2hex(txnid), self.addr],
            "jsonrpc": "2.0",
            "id": 0,
        }
        headers = {'content-type': 'application/json'}
        response = requests.post(
            addr, data=json.dumps(payload), headers=headers).json()

        tx = Transaction.unserialize_full(SerializationBuffer(hex2b(response['result'])))
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


    def transaction_sent(self, value):
        pass #value = 1 if txn was written, 0 if it already existed

    def transaction_send_error(self,error):
        # TODO maybe resend txn
        print(error)

    def send_txn(self, addr, txn):
        proxy = Proxy(addr)
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

            ts = int(time.time() * TIME_MULTIPLIER)

            if self.verify_txn(txn):
                #write txn to pend or db depending on timelock
                if txn.timelock:
                    self.pend[txn.txid] = TxnWrapper(txn, ts)
                    self.add_txn_to_balance_index(txn, self.pub_outs_pend)
                    for inp in txn.inputs:
                        output_txnw = self[inp.txid]
                        #set outputs to spent

                        output_txnw.utxos[inp.index] = False
                        self[inp.txid] = output_txnw

                        # delete output from pub_outs index
                        self.del_out_from_balance_index(
                            output_txnw.txn.outputs[inp.index].get_pubkeys(),
                            inp.txid, inp.index, self.pub_outs)
                    print('txn {} ACCEPTED(PENDING)\n'.format(b2hex(txid)))
                else:
                    self.write_txn_to_db(txn, ts)
                    print('txn {} ACCEPTED\n'.format(b2hex(txid)))


            self.remove_txn_from_mempool_and_return(txid)
            self.print_balances()
            print('\n')

    def write_txn_to_db(self,txn,ts):
        # set all outputs to spent
        for inp in txn.inputs:
            output_txnw = self[inp.txid]
            output_txnw.utxos[inp.index] = False
            self[inp.txid] = output_txnw

            # delete output from pub_outs index
            self.del_out_from_balance_index(
                output_txnw.txn.outputs[inp.index].get_pubkeys(),
                inp.txid, inp.index, self.pub_outs)

        # write txn to db
        self[txn.txid] = TxnWrapper(txn, ts)
        # update index
        self.add_txn_to_balance_index(txn, self.pub_outs)

    def verify_txn(self, txn, check_pend=True):
        txid = txn.txid
        if txid in self:
            print('Trasaction {} is already stored'.format(b2hex(txid)))
            self.remove_txn_from_mempool_and_return(txid)
            return False

        has_coins = 0
        for inp in txn.inputs:
            if inp.txid == NO_HASH:  # skip dummy inputs
                continue
            try:
                output_txnw = self[inp.txid]
                spent_output = output_txnw.txn.outputs[inp.index]
                has_coins += spent_output.amount
            except KeyError:
                if inp.txid in self.pend:
                    print('Transaction %s is still locked!' % b2hex(
                        txn.txid))
                    print("Invalid input on transaction %s!" % b2hex(
                        txn.txid))
                    self.remove_txn_from_mempool_and_return(txid)
                    return False

            # verify signatures
            #Case timeout reached
            if time.time() * TIME_MULTIPLIER - output_txnw.timestamp >= \
                    spent_output.htlc_timeout * TIMEOUT_CONST:
                #Check pubkey and pubkey2
                if (not verify_sig(txn.txid, spent_output.pubkey,
                                   inp.signature) or
                        not verify_sig(txn.txid, spent_output.pubkey2,
                                       inp.signature2)):
                        print("Invalid signatures on transaction %s!" % b2hex(
                            txn.txid))
                        self.remove_txn_from_mempool_and_return(txid)
                        return False

            #Case that timeout isnt reached yet
            else:
                if not sha256(inp.htlc_preimage) == spent_output.htlc_hashlock:
                    print("Preimage doesn't match hashlock on transaction "
                          "%s!" % b2hex(
                        txn.txid))
                    self.remove_txn_from_mempool_and_return(txid)
                    return False

                if (not verify_sig(txn.txid, spent_output.htlc_pubkey,
                                   inp.signature)):
                        print("Invalid signatures on transaction %s!" % b2hex(
                            txn.txid))
                        self.remove_txn_from_mempool_and_return(txid)
                        return False

            if check_pend:
                check = self.check_pend_replacement(txn)
                if not check[0]:
                    print(
                        'txn %s tries to replace a txn for which it is not allowed' %
                        b2hex(txn.txid))
                    self.remove_txn_from_mempool_and_return(txid)
                    return False

                #if a matching txn was found, the outputs are already set to
                # spent
                if not check[1]:
                    # check if outputs are unspent
                    if not output_txnw.utxos[inp.index]:
                            print("Transaction %s uses spent outputs!" % b2hex(
                                txn.txid))
                            self.remove_txn_from_mempool_and_return(txid)
                            return False


        spends_coins = sum([out.amount for out in txn.outputs])
        if not has_coins == spends_coins:
            print('Sum of Output Amounts doesnt equal sum of Input Amounts in txn %s' % b2hex(
                        txn.txid))
            self.remove_txn_from_mempool_and_return(txid)
            return False


        return True

    def remove_txn_from_mempool_and_return(self, txid):
        self.mempool = [txn for txn in self.mempool if txn[0] != txid]
        self.processing = False
        print('\n')


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