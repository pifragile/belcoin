import time
import os
import shutil
from os.path import expanduser

from belcoin_node.storage import Storage
from belcoin_node.config import test_transactions

import errno

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


storage = Storage('localhost:{}'.format(str(12345)),
                       [], 0,
                       None)

storage.testing = True


txns = test_transactions
t = time.time()
for txn in txns:
    storage.add_to_mempool(txn)
storage.add_block_to_queue_test({'time': time.time(),
                                      'txns': [tx.txid for tx in txns]})
storage.try_process()
print(time.time() - t)