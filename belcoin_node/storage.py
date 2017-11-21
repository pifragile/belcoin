import sys
import os
import time
import requests
import json
import plyvel
from os.path import join, expanduser
from belcoin_node.txnwrapper import TxnWrapper
from belcoin_node.util import PUBS
from belcoin_node.pendingdb import PendingDB
from belcoin_node.config import VERBOSE, COINBASE
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
        self.txns_processed = 0
        self.missing_txns = []
        self.block_queue = []
        self.current_time = 0

        #create genesis transaction:
        gentxn = COINBASE
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
        """
        Adds a transaction txn to index index which is either pub_outs or
        pub_outs_pend
        """
        txid = txn.txid
        for i in range(len(txn.outputs)):
            o = txn.outputs[i]
            for p in o.get_pubkeys():
                if p in index:
                        index[p].add((txid, i))
                else:
                    index[p] = set([(txid, i)])

    def del_out_from_balance_index(self, pubkeys, txid, i, index):
        """
        Removes an ouput (txid,i) from index index which is either pub_outs or
        pub_outs_pend
        """
        index_name = "pub_outs" if index == self.pub_outs else "pub_outs_pend"
        for pubkey in pubkeys:
            if pubkey not in index:
                if VERBOSE:
                    print('trying to delete output for a pubkey which doesn\'t '
                          'exist from ' + index_name)
                continue

            try:
                index[pubkey].remove((txid, i))
            except KeyError:
                if VERBOSE:
                    print('trying to delete output which doesn\'t exist from '+
                          index_name)
                continue

    def get_balance(self, pubkey, index):
        """
        Returns the balances bal, bal_partial bal_htlc for a given public
        key, from a ceratin index (pub_outs or pub_outs_pend)

        bal: balance totally ownded by pubkey
        bal_partial: balance for transaction where the owner only has one
        pubkey in the output
        bal_htlc: balance owned, if the htlc preimage can be provided within
        the timeout
        """
        bal = 0
        bal_partial = 0
        bal_htlc = 0

        if pubkey not in index:
            return [0, 0, 0]

        for (txid, i) in index[pubkey]:

            txnw = self[txid] if index == self.pub_outs else self.pend[txid]

            o = txnw.txn.outputs[i]
            #Case timeout reached
            if pubkey in [o.pubkey, o.pubkey2] and self.current_time * \
                    TIME_MULTIPLIER - txnw.timestamp >= o.htlc_timeout * TIMEOUT_CONST:
                if o.pubkey == o.pubkey2:
                    bal += o.amount
                else:
                    bal_partial += o.amount

            #Case time out no reached
            if pubkey == o.htlc_pubkey and self.current_time * \
                    TIME_MULTIPLIER - txnw.timestamp < o.htlc_timeout * TIMEOUT_CONST:
                bal_htlc += o.amount

        return [bal, bal_partial, bal_htlc]

    def print_balances(self):
        """
        prints an overview over the balances to terminal
        """
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
                if self.current_time * TIME_MULTIPLIER - txnw.timestamp > tx.timelock * \
                        TIMELOCK_CONST:
                    return False, True
                if txn.seq <= tx.seq:
                    return False, True
                self.del_from_pending(tx)
                return True, True
        return True, False


    def comparable_input(self, inp):
        """
        :return: A hashable form of a given input
        """
        return {
            'txid': b2hex(inp.txid),
            'index': inp.index,
            # 'signature': b2hex(inp.signature),
            # 'signature2': b2hex(inp.signature2),
            # 'htlc_preimage': b2hex(inp.htlc_preimage)
        }



    @replicated
    def update_pend(self):
        """
        Called by the RAFT leader periodically
        Checks for transactions which were pending (have a timelock) if the
        timelock exceeded and if yes, check if txn is valid and write to db

        """
        #TODO make list ordered and stop when a txn was found, that cant be
        # written
        for txid, txnw in self.pend.db:
            txnw = TxnWrapper.unserialize(SerializationBuffer(txnw))
            timestamp = txnw.timestamp
            timelock = txnw.txn.timelock
            if self.current_time * TIME_MULTIPLIER - timestamp > timelock * \
                        TIMELOCK_CONST:

                self.del_from_pending(txnw.txn)
                if self.verify_txn(txnw.txn, check_pend=False):
                    self.write_txn_to_db(txnw.txn, timestamp)
                    if VERBOSE:
                        print('Transaction {} was pending and now put in '
                              'db'.format(b2hex(txid)))
                else:
                    if VERBOSE:
                        print('Transaction {} was pending and could not be '
                              'written to db, see reason above'.format(b2hex(
                              txid)))

    def del_from_pending(self, tx):
        """
        deletes a txn from the pend db
        """
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
        """
        Broadcasts a txn to all nodes rpc interfaces
        """
        if not reactor.running:
            reactor.callWhenRunning(self.broadcast_txn, txn)
            reactor.run()
        else:
            for addr in list(self.bcnode.rpc_peers.values()):#[:2]:
                reactor.callLater(0, self.send_txn, addr, txn)


    def send_block(self):
        """
        Called by the leader when a new block is ready
        Creates a block (=List of txn hashes) and initiates RAFT
        """
        txns = self.mempool[:BLOCK_SIZE]
        now = time.time() if time.time() > self.current_time else self.current_block
        block = {'time': now, 'txns' : [item[0] for item in txns]}
        #if set(block) not in map(set, self.block_queue):
        if set(block) != set(self.current_block):
            self.add_block_to_queue(block)

    def try_process(self):
        if not self.processing:
            if len(self.block_queue) > 0:
                block = self.block_queue[0]
                self.processing = True
                self.leader_processing = True
                self.find_missing_transactions(block)
                del self.block_queue[0]
                self.processing = False
                self.leader_processing = False

    @replicated
    def add_block_to_queue(self, block):
        if self._isLeader():
            print('Leader')
        self.adding_block = True
        #if set(block) not in map(set, self.block_queue):
        self.current_time = block['time']
        self.update_pend()
        block = block['txns']
        if set(block) != set(self.current_block):
            if VERBOSE:
                print('received block {}'.format(b2hex(merkle_root(block))))
            self.block_queue.append(block)
        self.adding_block = False
        self.try_process()



    #@replicated
    def find_missing_transactions(self, block):
        """
        If some txns were not in the mempool of this node, it sends a request to
        the leader to get the txn
        """
        if VERBOSE:
            print('received block {}'.format(b2hex(merkle_root(block))))
        self.current_block = block
        self.missing_txns = []
        for txid in block:
            tx = [txn for txn in self.mempool if txn[0] == txid]
            if len(tx) == 0:
                self.missing_txns.append(txid)
        if len(self.missing_txns) > 0:
                self.request_missing_transactions()
        else:
            self.process_block(block)

    def request_missing_transactions(self):
        """
        requests txns from leader
        """
        for txn in self.missing_txns:
            self.request_missing_transaction(txn)

    def request_missing_transaction(self, txnid, i = 0):
        """
        Requests one txn from the leader, this request needs to be blocking
        because one cannot continue with the block until all txns are
        available
        """
        # tx = None
        # rpc_peers = list(self.bcnode.rpc_peers.values())
        # i = 0
        # while tx is None:
        #     # try:
        #     #     addr = self.bcnode.rpc_peers[self._getLeader()]
        #     # except KeyError:
        #     addr = rpc_peers[i % len(rpc_peers)]
        #     if VERBOSE:
        #         print('requesting transaction {} from {}'.format(b2hex(txnid),
        #                                                          addr))
        #     payload = {
        #         "method": "req_txn",
        #         "params": [b2hex(txnid), self.addr],
        #         "jsonrpc": "2.0",
        #         "id": 0,
        #     }
        #     headers = {'content-type': 'application/json'}
        #     response = requests.post(
        #         addr, data=json.dumps(payload), headers=headers).json()
        #     if response['result'] == 0:
        #         i += 1
        #
        #         #check if tx is now in mempool, there can be strange race
        #         # conditions when leader changes in a bad moment
        #         if i % len(rpc_peers) == 0:
        #             txn_list = [txn for txn in self.mempool if txn[0] == txnid]
        #             if len(txn_list) > 0:
        #                 tx = txn_list[0]
        #         continue
        #
        #     tx = Transaction.unserialize_full(SerializationBuffer(hex2b(response['result'])))
        #     i += 1
        #
        #
        # if VERBOSE:
        #     print('node {} received txn {}'.format(self.nid,
        #                                            b2hex(tx.txid)))
        #
        # if len([txn for txn in self.mempool if txn[0] ==
        #         tx.txid]) == 0:
        #     self.mempool.append((tx.txid, tx))
        #     if VERBOSE:
        #         print('Txn {} put in mempool on node {}.'.format(b2hex(
        #             tx.txid), self.nid))
        # else:
        #     if VERBOSE:
        #         print('Txn {} already in mempool on node {}.'.format(
        #             b2hex(tx.txid), self.nid))

        if not reactor.running:
            reactor.callWhenRunning(self.request_missing_transaction(), txnid)
            reactor.run()
        else:
                reactor.callLater(0, self.req_txn, txnid, i)




    def transaction_sent(self, value):
        """
        Callback to be called after a txn was successfully sent
        """
        pass #value = 1 if txn was written, 0 if it already existed

    def transaction_send_error(self,error):
        """
        Callback to be called when an error happened while sending a txn
        """
        # TODO maybe resend txn
        print(error)

    def send_txn(self, addr, txn):
        """
        send a txn to addr
        """
        proxy = Proxy(addr)
        d = proxy.callRemote('puttxn', txn, False)
        d.addCallbacks(self.transaction_sent,
                       self.transaction_send_error)
    def req_txn(self, txid, i):
        """
        request a txn
        """
        i += 1
        rpc_peers = list(self.bcnode.rpc_peers.values())
        addr = rpc_peers[i % len(rpc_peers)]
        if VERBOSE:
            print('requesting transaction {} from {}'.format(b2hex(txid),
                                                                      addr))
        proxy = Proxy(addr)
        d = proxy.callRemote('req_txn', b2hex(txid), self.addr)
        d.addCallback(self.transaction_received, i=i, txid=txid)
        d.addErrback(self.transaction_receive_error)

    def transaction_received(self, txn, i, txid):
        if txn == 0:
            self.request_missing_transaction(txid, i=i)
            return

        tx = Transaction.unserialize_full(SerializationBuffer(hex2b(txn)))
        if VERBOSE:
            print('node {} received txn {}'.format(self.nid,
                                                   b2hex(tx.txid)))

        if len([txn for txn in self.mempool if txn[0] ==
                tx.txid]) == 0:
            self.mempool.append((tx.txid, tx))
            self.missing_txns.remove(txid)
            if VERBOSE:
                print('Txn {} put in mempool on node {}.'.format(b2hex(
                    tx.txid), self.nid))
        else:
            if VERBOSE:
                print('Txn {} already in mempool on node {}.'.format(
                    b2hex(tx.txid), self.nid))
        if len(self.missing_txns) == 0:
            self.process_block(self.current_block)

    def transaction_receive_error(self,err):
        print(err)

    def process_block(self, block):
        """
        Process a block(= list of txn hashes)

        Check if all txns are in mempool (sould always be the case because
        find_missing_transactions() was called before)

        For all transactions: if it is valid, check if there is a timelock and
        either write to pend or to db

        """

        for txid in block:
            tx = [txn[1] for txn in self.mempool if txn[0] == txid]

            if len(tx) == 0:
                raise InvalidTransactionError(
                    "VERY STRANGE ERROR".format(self.nid))
            if len(tx) > 1:
                raise InvalidTransactionError(
                    "COLLISION OOOHHH MYYYY GOOOOD".format(self.nid))
            txn = tx[0]

            ts = int(self.current_time * TIME_MULTIPLIER)

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
                    if VERBOSE:
                        print('txn {} ACCEPTED(PENDING)\n'.format(b2hex(txid)))
                else:
                    self.write_txn_to_db(txn, ts)
                    if VERBOSE:
                        print('txn {} ACCEPTED\n'.format(b2hex(txid)))
            self.txns_processed+=1


            self.remove_txn_from_mempool_and_return(txid)
            if VERBOSE:
                self.print_balances()
                print('\n')

        print('finished block {}'.format(b2hex(merkle_root(block))))
        print('txns processed : {}'.format(str(self.txns_processed)))


    def write_txn_to_db(self,txn,ts):
        """
        writes a txn to db:
            1. set all outputs to spend
            2. delete outputs from pub_outs index
            3. write to db
            4. update pub_outs index with the outputs of this txn
        """
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
        """
        Verifies a txn:

        1. Check if txn already exists in db
        2. Check if txn is locked by a timelock
        3. Verify signatures
            Case 1: HTLC timeout reached
            Case 2: HTLC timeout not reached
        4. If check_pend is True, check if there is a conflicting txn in
        pend( uses the same inputs) and if yes, if it can be replaced.
        5. Check if the transaction uses spent outputs
        6. Check if the sum of all input amouts matches the sum of all output amounts

        :param check_pend: True if checks concerning replacements in pend
        should be performed. Should be set to False if you want to verify
        txns that are in pend already

        """
        txid = txn.txid
        if txid in self:
            if VERBOSE:
                print('Trasaction {} is already stored'.format(b2hex(txid)))
            self.remove_txn_from_mempool_and_return(txid)
            return False

        has_coins = 0
        for inp in txn.inputs:
            if inp.txid == NO_HASH:  # skip dummy inputs
                continue
            try:
                output_txnw = self[inp.txid]
                try:
                    spent_output = output_txnw.txn.outputs[inp.index]
                except IndexError:
                    if VERBOSE:
                        print("Invalid input on transaction %s (input "
                              "index out of bounds)!" % b2hex(
                            txn.txid))
                    self.remove_txn_from_mempool_and_return(txid)
                    return False
                has_coins += spent_output.amount
            except KeyError:
                if inp.txid in self.pend:
                    if VERBOSE:
                        print('Transaction %s is still locked!' % b2hex(
                            txn.txid))
                if VERBOSE:
                    print("Invalid input on transaction %s!" % b2hex(
                        txn.txid))
                self.remove_txn_from_mempool_and_return(txid)
                return False

            # verify signatures
            #Case timeout reached
            if self.current_time * TIME_MULTIPLIER - output_txnw.timestamp >= \
                    spent_output.htlc_timeout * TIMEOUT_CONST:
                #Check pubkey and pubkey2
                if (not verify_sig(txn.txid, spent_output.pubkey,
                                   inp.signature) or
                        not verify_sig(txn.txid, spent_output.pubkey2,
                                       inp.signature2)):
                        if VERBOSE:
                            print("Invalid signatures on transaction %s!" % b2hex(
                                txn.txid))
                        self.remove_txn_from_mempool_and_return(txid)
                        return False

            #Case that timeout isnt reached yet
            else:
                if not sha256(inp.htlc_preimage) == spent_output.htlc_hashlock:
                    if VERBOSE:
                        print("Preimage doesn't match hashlock on transaction "
                              "%s!" % b2hex(
                            txn.txid))
                    self.remove_txn_from_mempool_and_return(txid)
                    return False

                if (not verify_sig(txn.txid, spent_output.htlc_pubkey,
                                   inp.htlc_signature)):
                        if VERBOSE:
                            print("Invalid htlc signatures on transaction %s!" %
                                  b2hex(
                                txn.txid))
                        self.remove_txn_from_mempool_and_return(txid)
                        return False

            if check_pend:
                check = self.check_pend_replacement(txn)
                # check[0] is True if the transaction is not conflicting
                # with a transaction in pend which it is not allowd to replace
                #  or there simply is no conflicting txn in pend

                if not check[0]:
                    if VERBOSE:
                        print(
                            'txn %s tries to replace a txn for which it is not allowed' %
                            b2hex(txn.txid))
                    self.remove_txn_from_mempool_and_return(txid)
                    return False

                #check[1] is true if a conflicting txn was found in pend
                #if this is the case, the outputs referenced by the inputs of
                #  theconflicting transaction have already be set to spent
                # and therefore don't need ti be checked again
                if not check[1]:
                    # check if outputs are unspent
                    if not output_txnw.utxos[inp.index]:
                            if VERBOSE:
                                print("Transaction %s uses spent outputs!" % b2hex(
                                    txn.txid))
                            self.remove_txn_from_mempool_and_return(txid)
                            return False


        spends_coins = sum([out.amount for out in txn.outputs])
        if not has_coins == spends_coins:
            if VERBOSE:
                print('Sum of Output Amounts doesnt equal sum of Input Amounts in txn %s' % b2hex(
                            txn.txid))
            self.remove_txn_from_mempool_and_return(txid)
            return False
        return True

    def remove_txn_from_mempool_and_return(self, txid):
        """
        remove a txn from mempool
        """
        self.mempool = [txn for txn in self.mempool if txn[0] != txid]
        if VERBOSE:
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