from tesseract.transaction import Input,Output,Transaction
from tesseract.crypto import generate_keypair,sign
from belcoin_node.util import PRIVS, PUBS, HASHLOCKS, PREIMAGES


def generate_txns():
    txns = []
    txid = genesis_txn().txid
    for i in range(len(PUBS)):
        txn = Transaction(
            [Input(txid, i)],
            [Output(100, PUBS[(i+1) % 100], PUBS[(i+1) % 100]),
             Output(900, PUBS[i], PUBS[i])]
        )
        for inp in txn.inputs:
            inp.signature = sign(txn.txid, PRIVS[i])
            inp.signature2 = sign(txn.txid, PRIVS[i])
        txns.append(txn)
    return txns

def generate_txns2():
    txns = []
    prev_txns = generate_txns()
    for i in range(len(prev_txns)):
        txid = prev_txns[i].txid
        txn = Transaction(
            [Input(txid, 1)],
            [Output(50, PUBS[(i+1) % 100], PUBS[(i+1) % 100]),
             Output(850, PUBS[i], PUBS[i])]
        )
        for inp in txn.inputs:
            inp.signature = sign(txn.txid, PRIVS[i])
            inp.signature2 = sign(txn.txid, PRIVS[i])
        txns.append(txn)
    return txns

def genesis_txn():
    outputs = [Output(1000, PUBS[i], PUBS[i]) for i in range(len(PUBS))]
    return Transaction([], outputs)