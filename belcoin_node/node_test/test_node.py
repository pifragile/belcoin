import io
import os
import shutil
from os.path import expanduser
from unittest import TestCase

import errno

import sys

from belcoin_node.storage import Storage
from belcoin_node.util import PUBS,PRIVS,HASHLOCKS,PREIMAGES
from belcoin_node.config import TIME_MULTIPLIER, COINBASE
from belcoin_node.txnwrapper import TxnWrapper
from tesseract.crypto import sign, sha256d
from tesseract.transaction import Input,Output,Transaction
import time
import gc


SO = sys.stdout
i = 0

class Test_test(TestCase):

    def get_time(self):
        return int(time.time() * TIME_MULTIPLIER)

    def busy_wait(self,dt):
        current_time = time.time()
        while (time.time() < current_time + dt):
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
        i += 1
    def tearDown(self):
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
            [Input(COINBASE.txid, 0)],
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
            [Input(COINBASE.txid, 99999)],
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
            [Input(COINBASE.txid, 0)],
            [Output(100, PUBS[0], PUBS[0], 10, HASHLOCKS[0], PUBS[1])])

        for inp in txn.inputs:
            inp.signature = sign(txn.txid, PRIVS[0])
            inp.signature2 = sign(txn.txid, PRIVS[0])

        self.storage[txn.txid] = TxnWrapper(txn, self.get_time())

        txn1 = Transaction(
            [Input(txn.txid, 0, htlc_preimage=PREIMAGES[0])],
            [Output(100, PUBS[0], PUBS[0])]
        )

        for inp in txn1.inputs:
            inp.htlc_signature = sign(txn1.txid, PRIVS[1])

        assert self.storage.verify_txn(txn1)

    def test_htlc_transactions_wrong_preimage(self):
        txn = Transaction(
            [Input(COINBASE.txid, 0)],
            [Output(100, PUBS[0], PUBS[0], 10, HASHLOCKS[0], PUBS[1])])

        for inp in txn.inputs:
            inp.signature = sign(txn.txid, PRIVS[0])
            inp.signature2 = sign(txn.txid, PRIVS[0])

        self.storage[txn.txid] = TxnWrapper(txn, self.get_time())

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
            [Input(COINBASE.txid, 0)],
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
            [Input(COINBASE.txid, 0)],
            [Output(1000, PUBS[0], PUBS[0])])

        for inp in txn.inputs:
            inp.signature = sign(txn.txid, PRIVS[0])
            inp.signature2 = sign(txn.txid, PRIVS[0])

        assert self.storage.verify_txn(txn)
        self.storage.mempool.append((txn.txid, txn))
        self.storage.process_block([txn.txid])

        txn1 = Transaction(
            [Input(COINBASE.txid, 0)],
            [Output(999, PUBS[0], PUBS[0]), Output(1, PUBS[0], PUBS[0])])

        for inp in txn1.inputs:
            inp.signature = sign(txn1.txid, PRIVS[0])
            inp.signature2 = sign(txn1.txid, PRIVS[0])

        self.storage.verify_txn(txn1)
        assert self.storage.verify_txn(txn1) is False
        output = out.getvalue().strip()
        print(output)
        assert 'spent outputs' in output

#TODO timing stuff, assertion that sum of balances is same and
# other tests on balance indeces


    def test_pending_transactions_wrong_seq_num(self):
        out = io.StringIO()
        sys.stdout = out
        self.storage.current_time = time.time()
        txn = Transaction(
            [Input(COINBASE.txid, 0)],
            [Output(1000, PUBS[1], PUBS[1], 10, HASHLOCKS[0], PUBS[0])],
            seq=0,
            timelock=12
        )
        for inp in txn.inputs:
            inp.signature = sign(txn.txid, PRIVS[0])
            inp.signature2 = sign(txn.txid, PRIVS[0])
        self.storage.mempool.append((txn.txid, txn))
        self.storage.process_block([txn.txid])
        self.storage.current_time = time.time()

        txn1 = Transaction(
            [Input(COINBASE.txid, 0)],
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
            [Input(COINBASE.txid, 0)],
            [Output(1000, PUBS[1], PUBS[1], 10, HASHLOCKS[0], PUBS[0])],
            seq=0,
            timelock=3
        )
        for inp in txn.inputs:
            inp.signature = sign(txn.txid, PRIVS[0])
            inp.signature2 = sign(txn.txid, PRIVS[0])
        self.storage.mempool.append((txn.txid, txn))
        self.storage.process_block([txn.txid])

        self.busy_wait(5)
        self.storage.current_time = time.time()
        self.storage.update_pend()
        txn1 = Transaction(
            [Input(COINBASE.txid, 0)],
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
        out = io.StringIO()
        sys.stdout = out
        self.storage.current_time = time.time()
        txn = Transaction(
            [Input(COINBASE.txid, 0)],
            [Output(1000, PUBS[1], PUBS[1], 10, HASHLOCKS[0], PUBS[0])],
            seq=0,
            timelock=3
        )
        for inp in txn.inputs:
            inp.signature = sign(txn.txid, PRIVS[0])
            inp.signature2 = sign(txn.txid, PRIVS[0])
        self.storage.mempool.append((txn.txid, txn))
        self.storage.process_block([txn.txid])

        self.busy_wait(2)

        self.storage.current_time = time.time()
        txn1 = Transaction(
            [Input(COINBASE.txid, 0)],
            [Output(1, PUBS[1], PUBS[1], 10, HASHLOCKS[0], PUBS[0]),
             Output(999, PUBS[1], PUBS[1], 10, HASHLOCKS[0], PUBS[0])],
            seq=2,
            timelock=3
        )
        for inp in txn1.inputs:
            inp.signature = sign(txn1.txid, PRIVS[0])
            inp.signature2 = sign(txn1.txid, PRIVS[0])

        assert self.storage.verify_txn(txn1)