import io
import os
import shutil
import sys
import time
import gc
from os.path import expanduser
from unittest import TestCase
import errno
from belcoin_node.config import test_transactions
from belcoin_node.storage import Storage
from belcoin_node.util import PRIVS, HASHLOCKS, PREIMAGES
from belcoin_node.config import TIME_MULTIPLIER, COINBASE
from belcoin_node.txnwrapper import TxnWrapper
from belcoin_node.util import PUBS
from tesseract.crypto import sign, sha256d
from tesseract.transaction import Input, Output, Transaction

SO = sys.stdout
i = 0


class Test_test(TestCase):

    """
    For the tests to run, COINBASE has to be set to [createtxns.genesis_txn()]
    in the belcoin_node.config file
    """

    def get_time(self):
        return int(time.time() * TIME_MULTIPLIER)

    def busy_wait(self,dt):
        current_time = time.time()
        while (time.time() < current_time + dt):
            pass

    def calculate_balances(self):
        sum_bal = sum([sum(self.storage.get_balance(pub,
                                                      self.storage.pub_outs))
                            for pub in PUBS])
        sum_bal_pend = sum([sum(self.storage.get_balance(pub,
                                                      self.storage.pub_outs_pend))
                            for pub in PUBS])
        return sum_bal + sum_bal_pend
        pass

    def setUp(self):


        try:
            shutil.rmtree(expanduser('~/.belcoin'))
        except Exception:
            pass

        # create directory for databases
        try:
            os.makedirs(expanduser('~/.belcoin'))
        except OSError as exc:
            if (exc.errno == errno.EEXIST and
                    os.path.isdir(expanduser('~/.belcoin'))):
                pass
            else:
                raise

        global i
        self.storage = Storage('localhost:{}'.format(str(12345 + i)),
                               [], i,
                               None)
        self.storage.testing = True
        self.sum = self.calculate_balances()
        i += 1

    def tearDown(self):
        assert self.sum == self.calculate_balances()
        try:
            shutil.rmtree(expanduser('~/.belcoin'))
        except Exception:
            print('ERROR123')

        self.storage = None
        gc.collect()
        sys.stdout = SO

    def test_insert_in_db(self):
        txn = Transaction(
            [],
            [Output(1000, PUBS[0], PUBS[0])]
        )
        for inp in txn.inputs:
            inp.signature = sign(txn.txid, PRIVS[0])
            inp.signature2 = sign(txn.txid, PRIVS[0])

        self.storage[txn.txid] = TxnWrapper(txn, int(time.time() *
                                            TIME_MULTIPLIER))
        assert self.storage.get(txn.txid).txn == txn

    def test_invalid_signatures(self):
        txn = Transaction(
            [Input(COINBASE[0].txid, 0)],
            [Output(1000, PUBS[0], PUBS[0])]
        )
        for inp in txn.inputs:
            inp.signature = sign(txn.txid, PRIVS[0])
            inp.signature2 = sign(txn.txid, PRIVS[1])


        out = io.StringIO()
        sys.stdout = out
        assert self.storage.verify_txn(txn) is False
        output = out.getvalue().strip()
        print(output)
        assert 'Invalid signatures' in output

    def test_invalid_input(self):
        txn = Transaction(
            [Input(COINBASE[0].txid, 99999)],
            [Output(1000, PUBS[0], PUBS[0])]
        )
        for inp in txn.inputs:
            inp.signature = sign(txn.txid, PRIVS[0])
            inp.signature2 = sign(txn.txid, PRIVS[1])

        out = io.StringIO()
        sys.stdout = out
        assert self.storage.verify_txn(txn) is False
        output = out.getvalue().strip()
        print(output)
        assert 'Invalid input' in output

    def test_invalid_input2(self):
        txn = Transaction(
            [Input(sha256d(b'0'), 0)],
            [Output(1000, PUBS[0], PUBS[0])]
        )
        for inp in txn.inputs:
            inp.signature = sign(txn.txid, PRIVS[0])
            inp.signature2 = sign(txn.txid, PRIVS[1])

        out = io.StringIO()
        sys.stdout = out
        assert self.storage.verify_txn(txn) is False
        output = out.getvalue().strip()
        print(output)
        assert 'Invalid input' in output

    def test_htlc_transactions_correct_preimage(self):
        txn = Transaction(
            [Input(COINBASE[0].txid, 0)],
            [Output(100, PUBS[0], PUBS[0], 10, HASHLOCKS[0], PUBS[1])])

        for inp in txn.inputs:
            inp.signature = sign(txn.txid, PRIVS[0])
            inp.signature2 = sign(txn.txid, PRIVS[0])

        self.storage[txn.txid] = TxnWrapper(txn, self.get_time())
        self.storage.current_time = time.time()
        txn1 = Transaction(
            [Input(txn.txid, 0, htlc_preimage=PREIMAGES[0])],
            [Output(100, PUBS[0], PUBS[0])]
        )

        for inp in txn1.inputs:
            inp.htlc_signature = sign(txn1.txid, PRIVS[1])

        assert self.storage.verify_txn(txn1)

    def test_htlc_transactions_wrong_preimage(self):
        txn = Transaction(
            [Input(COINBASE[0].txid, 0)],
            [Output(100, PUBS[0], PUBS[0], 10, HASHLOCKS[0], PUBS[1])])

        for inp in txn.inputs:
            inp.signature = sign(txn.txid, PRIVS[0])
            inp.signature2 = sign(txn.txid, PRIVS[0])

        self.storage[txn.txid] = TxnWrapper(txn, self.get_time())
        self.storage.current_time = time.time()
        txn1 = Transaction(
            [Input(txn.txid, 0, htlc_preimage=PREIMAGES[1])],
            [Output(100, PUBS[0], PUBS[0])]
        )

        for inp in txn1.inputs:
            inp.htlc_signature = sign(txn1.txid, PRIVS[1])

        out = io.StringIO()
        sys.stdout = out
        assert self.storage.verify_txn(txn1) is False
        output = out.getvalue().strip()
        print(output)
        assert 'Preimage doesn' in output

    def test_unbalanced_transaction(self):
        txn = Transaction(
            [Input(COINBASE[0].txid, 0)],
            [Output(100, PUBS[1], PUBS[1]),
             Output(501, PUBS[0], PUBS[0])]
        )
        for inp in txn.inputs:
            inp.signature = sign(txn.txid, PRIVS[0])
            inp.signature2 = sign(txn.txid, PRIVS[0])
        out = io.StringIO()
        sys.stdout = out
        assert self.storage.verify_txn(txn) is False
        output = out.getvalue().strip()
        print(output)
        assert 'Sum of Output Amounts' in output

    def test_spent_outputs(self):
        out = io.StringIO()
        sys.stdout = out

        txn = Transaction(
            [Input(COINBASE[0].txid, 0)],
            [Output(1000, PUBS[0], PUBS[0])])

        for inp in txn.inputs:
            inp.signature = sign(txn.txid, PRIVS[0])
            inp.signature2 = sign(txn.txid, PRIVS[0])

        assert self.storage.verify_txn(txn)
        self.storage.add_to_mempool(txn)
        self.storage.add_block_to_queue_test({'time': time.time(), 'txns': [
            txn.txid]})
        self.storage.try_process()
        time.sleep(1)
        while self.storage.processing:
            pass

        txn1 = Transaction(
            [Input(COINBASE[0].txid, 0)],
            [Output(999, PUBS[0], PUBS[0]), Output(1, PUBS[0], PUBS[0])])

        for inp in txn1.inputs:
            inp.signature = sign(txn1.txid, PRIVS[0])
            inp.signature2 = sign(txn1.txid, PRIVS[0])

        self.storage.verify_txn(txn1)
        assert self.storage.verify_txn(txn1) is False
        output = out.getvalue().strip()
        print(output)
        assert 'spent outputs' in output


    def test_pending_transactions_wrong_seq_num(self):
        out = io.StringIO()
        sys.stdout = out
        self.storage.current_time = time.time()
        txn = Transaction(
            [Input(COINBASE[0].txid, 0)],
            [Output(1000, PUBS[1], PUBS[1], 10, HASHLOCKS[0], PUBS[0])],
            seq=0,
            timelock=12
        )
        for inp in txn.inputs:
            inp.signature = sign(txn.txid, PRIVS[0])
            inp.signature2 = sign(txn.txid, PRIVS[0])
        self.storage.add_to_mempool(txn)
        self.storage.add_block_to_queue_test({'time': time.time(), 'txns': [
            txn.txid]})
        self.storage.try_process()
        time.sleep(1)
        while self.storage.processing:
            pass

        txn1 = Transaction(
            [Input(COINBASE[0].txid, 0)],
            [Output(1, PUBS[1], PUBS[1], 10, HASHLOCKS[0], PUBS[0]),
             Output(999, PUBS[1], PUBS[1], 10, HASHLOCKS[0], PUBS[0])],
            seq=0,
            timelock=12
        )
        for inp in txn1.inputs:
            inp.signature = sign(txn1.txid, PRIVS[0])
            inp.signature2 = sign(txn1.txid, PRIVS[0])

        assert self.storage.verify_txn(txn1) is False
        output = out.getvalue().strip()
        assert 'tries to replace a txn for which it' in output

    def test_pending_transactions_too_late(self):
        out = io.StringIO()
        sys.stdout = out
        self.storage.current_time = time.time()
        txn = Transaction(
            [Input(COINBASE[0].txid, 0)],
            [Output(1000, PUBS[1], PUBS[1], 10, HASHLOCKS[0], PUBS[0])],
            seq=0,
            timelock=3
        )
        for inp in txn.inputs:
            inp.signature = sign(txn.txid, PRIVS[0])
            inp.signature2 = sign(txn.txid, PRIVS[0])
        self.storage.add_to_mempool(txn)
        self.storage.add_block_to_queue_test({'time': time.time(), 'txns': [
            txn.txid]})

        self.storage.try_process()
        self.busy_wait(5)
        self.storage.current_time = time.time()
        self.storage.update_pend()
        txn1 = Transaction(
            [Input(COINBASE[0].txid, 0)],
            [Output(1, PUBS[1], PUBS[1], 10, HASHLOCKS[0], PUBS[0]),
             Output(999, PUBS[1], PUBS[1], 10, HASHLOCKS[0], PUBS[0])],
            seq=1,
            timelock=3
        )
        for inp in txn1.inputs:
            inp.signature = sign(txn1.txid, PRIVS[0])
            inp.signature2 = sign(txn1.txid, PRIVS[0])

        assert self.storage.verify_txn(txn1) is False
        output = out.getvalue().strip()
        assert 'spent outputs' in output

    def test_pending_transactions_ok(self):
        # out = io.StringIO()
        # sys.stdout = out
        self.storage.current_time = time.time()
        txn = Transaction(
            [Input(COINBASE[0].txid, 0)],
            [Output(1000, PUBS[1], PUBS[1], 10, HASHLOCKS[0], PUBS[0])],
            seq=0,
            timelock=3
        )
        for inp in txn.inputs:
            inp.signature = sign(txn.txid, PRIVS[0])
            inp.signature2 = sign(txn.txid, PRIVS[0])
        self.storage.add_to_mempool(txn)
        self.storage.add_block_to_queue_test({'time': time.time(), 'txns': [
            txn.txid]})
        self.storage.try_process()
        self.busy_wait(2)
        self.calculate_balances()
        self.storage.current_time = time.time()
        txn1 = Transaction(
            [Input(COINBASE[0].txid, 0)],
            [Output(1, PUBS[1], PUBS[1], 10, HASHLOCKS[0], PUBS[0]),
             Output(999, PUBS[1], PUBS[1], 10, HASHLOCKS[0], PUBS[0])],
            seq=2,
            timelock=3
        )
        for inp in txn1.inputs:
            inp.signature = sign(txn1.txid, PRIVS[0])
            inp.signature2 = sign(txn1.txid, PRIVS[0])

        self.storage.add_to_mempool(txn1)
        self.storage.add_block_to_queue_test({'time': time.time(), 'txns': [
            txn1.txid]})
        self.storage.try_process()
        self.busy_wait(2)
        while self.storage.processing:
            pass

    def test_pending_txns_with_block(self):
        out = io.StringIO()
        sys.stdout = out
        self.storage.current_time = time.time()
        txn = Transaction(
            [Input(COINBASE[0].txid, 0)],
            [Output(1000, PUBS[1], PUBS[1], 10, HASHLOCKS[0], PUBS[0])],
            seq=0,
            timelock=3
        )
        for inp in txn.inputs:
            inp.signature = sign(txn.txid, PRIVS[0])
            inp.signature2 = sign(txn.txid, PRIVS[0])
        self.storage.add_to_mempool(txn)
        self.storage.add_block_to_queue_test({'time': time.time(), 'txns': [
            txn.txid]})
        self.storage.try_process()
        self.busy_wait(4)
        self.storage.current_time = time.time()
        self.storage.update_pend()
        txn1 = Transaction(
            [Input(COINBASE[0].txid, 0)],
            [Output(1, PUBS[1], PUBS[1], 10, HASHLOCKS[0], PUBS[0]),
             Output(999, PUBS[1], PUBS[1], 10, HASHLOCKS[0], PUBS[0])],
            seq=1,
            timelock=3
        )
        for inp in txn1.inputs:
            inp.signature = sign(txn1.txid, PRIVS[0])
            inp.signature2 = sign(txn1.txid, PRIVS[0])

        self.storage.add_to_mempool(txn1)
        self.storage.add_block_to_queue_test({'time': time.time(), 'txns': [
            txn1.txid]})
        self.storage.try_process()
        time.sleep(1)
        while self.storage.processing:
            pass
        output = out.getvalue().strip()
        assert 'spent outputs' in output

    def test_batch_for_profiler(self):
        #For the test to work set COINBASE to
        #createtxns2.genesis_txn_list_batch()

        t = time.time()
        txns = test_transactions
        for txn in txns:
            self.storage.add_to_mempool(txn)
        self.storage.add_block_to_queue_test({'time': time.time(),
                                              'txns': [tx.txid for tx in txns]})
        self.storage.try_process()
        print(time.time()-t)

