from tesseract.transaction import Input,Output,Transaction
from tesseract.crypto import generate_keypair,sign
from belcoin_node.util import PRIVS, PUBS


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

def genesis_txn():
    outputs = [Output(1000, PUBS[i], PUBS[i]) for i in range(5)]
    outputs2 = [Output(500, PUBS[i], PUBS[i]) for i in range(5)]
    outputs3 = [Output(100, PUBS[i], PUBS[i]) for i in range(5)]
    #return Transaction([], outputs)
    return Transaction([], outputs + outputs2 + outputs3)