from tesseract.transaction import Input,Output,Transaction
from tesseract.crypto import generate_keypair,sign
from belcoin_node.util import PRIVS, PUBS, HASHLOCKS, PREIMAGES


def generate_txns():
    txns = []
    txid = genesis_txn().txid
    for i in range(5):
        txn = Transaction(
            [Input(txid, i)],
            [Output(100, PUBS[(i+1) % 5], PUBS[(i+1) % 5]),
             Output(900, PUBS[i], PUBS[i])]
        )
        for inp in txn.inputs:
            inp.signature = sign(txn.txid, PRIVS[i])
            inp.signature2 = sign(txn.txid, PRIVS[i])
        txns.append(txn)
    return txns



def generate_conflicting_txns():
    txns = []
    txid = genesis_txn().txid
    for i in range(5):
        txn = Transaction(
            [Input(txid, i)],
            [Output(101, PUBS[(i+1) % 5], PUBS[(i+1) % 5]),
             Output(899, PUBS[i], PUBS[i])]
        )
        for inp in txn.inputs:
            inp.signature = sign(txn.txid,PRIVS[i])
            inp.signature2 = sign(txn.txid,PRIVS[i])
        txns.append(txn)
    return txns

def generate_unbalaced_txn():
    txn = Transaction(
        [Input(genesis_txn().txid, 5), Input(genesis_txn().txid, 10)],
        [Output(100, PUBS[1], PUBS[1]),
         Output(501, PUBS[0], PUBS[0])]
    )
    for inp in txn.inputs:
        inp.signature = sign(txn.txid, PRIVS[0])
        inp.signature2 = sign(txn.txid, PRIVS[0])
    return [txn]


def generate_partial_txns():
    txns = []
    txid = genesis_txn().txid
    for i in range(5):
        txn = Transaction(
            [Input(txid, i)],
            [Output(100, PUBS[(i+1) % 5], PUBS[(i+2) % 5]),
             Output(900, PUBS[i], PUBS[i])]
        )
        for inp in txn.inputs:
            inp.signature = sign(txn.txid, PRIVS[i])
            inp.signature2 = sign(txn.txid, PRIVS[i])
        txns.append(txn)
    return txns

def generate_htlc_txns():
    txns = []
    txid = genesis_txn().txid
    for i in range(5):
        txn = Transaction(
            [Input(txid, i + 10)],
            [Output(100, PUBS[i], PUBS[i], 10, HASHLOCKS[i], PUBS[(i + 1) %
                                                                    5])]
        )
        for inp in txn.inputs:
            inp.signature = sign(txn.txid, PRIVS[i])
            inp.signature2 = sign(txn.txid, PRIVS[i])
        txns.append(txn)
    return txns

def generate_htlc_txns2():
    txns = []
    for i in range(5):
        txid = generate_htlc_txns()[i].txid
        txn = Transaction(
            [Input(txid, 0, htlc_preimage=PREIMAGES[i])],
            [Output(100, PUBS[i], PUBS[i])]
        )
        for inp in txn.inputs:
            inp.htlc_signature = sign(txn.txid, PRIVS[(i + 1) % 5])
        txns.append(txn)
    return txns

def generate_pending_txns():
    txns = []
    txid = genesis_txn().txid
    for i in range(5):
        txn = Transaction(
            [Input(txid, i + 10)],
            [Output(100, PUBS[i], PUBS[i], 10, HASHLOCKS[i], PUBS[(i + 1) %
                                                                    5])],
            seq=0,
            timelock=12
        )
        for inp in txn.inputs:
            inp.signature = sign(txn.txid, PRIVS[i])
            inp.signature2 = sign(txn.txid, PRIVS[i])
        txns.append(txn)
    return txns

def generate_pending_txns2():
    txns = []
    txid = genesis_txn().txid
    for i in range(5):
        txn = Transaction(
            [Input(txid, i + 10)],
            [Output(50, PUBS[i], PUBS[i], 15, HASHLOCKS[i], PUBS[(i + 1) %
                                                                    5]),
             Output(50, PUBS[i], PUBS[i])
             ],
            seq=1,
            timelock=5
        )
        for inp in txn.inputs:
            inp.signature = sign(txn.txid, PRIVS[i])
            inp.signature2 = sign(txn.txid, PRIVS[i])
        txns.append(txn)
    return txns

def generate_conflicting_txn_pend():
    txid = genesis_txn().txid
    txn = Transaction(
        [Input(txid, 10), Input(txid, 5)],
        [
         Output(600, PUBS[0], PUBS[0])
         ]
    )
    for inp in txn.inputs:
        inp.signature = sign(txn.txid, PRIVS[0])
        inp.signature2 = sign(txn.txid, PRIVS[0])
    return [txn]


def generate_many_txns():
    prev = genesis_txn()
    txns = []
    for j in range(1000):
       txn = Transaction(
            [Input(prev.txid, 0)],
            [Output(1000, PUBS[(j + 1) % 2], PUBS[(j + 1) % 2])]
       )
       for inp in txn.inputs:
            inp.signature = sign(txn.txid, PRIVS[j % 2])
            inp.signature2 = sign(txn.txid, PRIVS[j % 2])
       txns.append(txn)
       prev = txn

    return txns

#problem is that if txns dont arrive in the specified order, it does not work
def generate_many_txns2():
    prev = genesis_txn()
    txns = []
    for j in range(1000):
       txn = Transaction(
            [Input(prev.txid, 0)],
            [Output(1000 - 1 - j, PUBS[0], PUBS[0]),
             Output(1, PUBS[1], PUBS[1])]
       )
       for inp in txn.inputs:
            inp.signature = sign(txn.txid, PRIVS[0])
            inp.signature2 = sign(txn.txid, PRIVS[0])
       txns.append(txn)
       prev = txn
    return txns

def genesis_txn():
    outputs = [Output(1000, PUBS[i], PUBS[i]) for i in range(5)]
    outputs2 = [Output(500, PUBS[i], PUBS[i]) for i in range(5)]
    outputs3 = [Output(100, PUBS[i], PUBS[i]) for i in range(5)]
    #return Transaction([], outputs)
    return Transaction([], outputs + outputs2 + outputs3)