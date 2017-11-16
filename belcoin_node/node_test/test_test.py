import os
import shutil
from os.path import expanduser
from unittest import TestCase

import errno

from belcoin_node.storage import Storage
from belcoin_node.util import PUBS,PRIVS
from belcoin_node.config import TIME_MULTIPLIER
from belcoin_node.txnwrapper import TxnWrapper
from tesseract.crypto import sign
from tesseract.transaction import Input,Output,Transaction
import time



txn = Transaction(
    [Input(b'0', 0)],
    [Output(1000, PUBS[0], PUBS[0])]
)
for inp in txn.inputs:
    inp.signature = sign(txn.txid, PRIVS[0])
    inp.signature2 = sign(txn.txid, PRIVS[0])

class Test_test(TestCase):
    def setUp(self):
        # create directory for databases
        try:
            os.makedirs(expanduser('~/.belcoin'))
        except OSError as exc:
            if (exc.errno == errno.EEXIST and
                    os.path.isdir(expanduser('~/.belcoin'))):
                pass
            else:
                raise
        self.storage = Storage('localhost:12345', [], 0, None)

    def tearDown(self):
        shutil.rmtree(expanduser('~/.belcoin'))

    def test_test1(self):
        print(txn.to_dict())
        self.storage[txn.txid] = TxnWrapper(txn, int(time.time() *
                                            TIME_MULTIPLIER))
        assert self.storage.get(txn.txid).txn == txn
