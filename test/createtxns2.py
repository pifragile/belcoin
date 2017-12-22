from tesseract.transaction import Input,Output,Transaction
from tesseract.crypto import generate_keypair,sign
from belcoin_node.util import PRIVS, PUBS, HASHLOCKS, PREIMAGES
from belcoin_node.crypto.crypto import sign as sign2
from tesseract.util import b2hex


"""
This File is used to generate Transactions for testing purposes
"""

def generate_txns():
    txns = []
    txid = genesis_txn().txid
    for i in range(len(PUBS)):
        txn = Transaction(
            [Input(txid, i)],
            [Output(1, PUBS[(i+1) % 100], PUBS[(i+1) % 100]),
             Output(999, PUBS[i], PUBS[i])]
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


def generate_many_txns():
    txns = []
    all_txns = []
    prev_txns = generate_txns()
    for j in range(10):
        for i in range(len(prev_txns)):
            txid = prev_txns[i].txid
            txn = Transaction(
                [Input(txid, 1)],
                [Output(1, PUBS[(i+1) % len(PUBS)], PUBS[(i+1) % len(PUBS)]),
                 Output(998 - j, PUBS[i], PUBS[i])]
            )
            for inp in txn.inputs:
                inp.signature = sign(txn.txid, PRIVS[i])
                inp.signature2 = sign(txn.txid, PRIVS[i])
            txns.append(txn)
        prev_txns = txns
        all_txns.append(txns)
        txns = []

    return [item for sublist in all_txns for item in sublist]

def generate_many_txns2():
    txns = []
    prev_txns = []#genesis_txn1()
    for i in range(1000):
        txid = prev_txns.txid
        txn = Transaction(
            [Input(txid, i)],
            [Output(1, PUBS[(i+1) % len(PUBS)], PUBS[(i+1) % len(PUBS)])]
        )
        for inp in txn.inputs:
            inp.signature = sign(txn.txid, PRIVS[i % len(PUBS)])
            inp.signature2 = sign(txn.txid, PRIVS[i % len(PUBS)])
        txns.append(txn)

    return txns


def generate_txns_batch():
    txns = []
    gen_txns = genesis_txn_list_batch()
    for j in range(100):
        for i in range(len(PUBS)):
            txn = Transaction(
                [Input(gen_txns[100*j + i].txid, 0)],
                [Output(1, PUBS[(i+1) % 100], PUBS[(i+1) % 100]),
                 Output(999 - j, PUBS[i], PUBS[i])]
            )
            for inp in txn.inputs:
                inp.signature = sign(txn.txid, PRIVS[i])
                inp.signature2 = sign(txn.txid, PRIVS[i])
            txns.append(txn)
    return txns

def generate_txns_batch_ll():
    txns = []
    gen_txns = genesis_txn_list_batch()
    for j in range(100):
        for i in range(len(PUBS)):
            txn = Transaction(
                [Input(gen_txns[100*j + i].txid, 0)],
                [Output(1, PUBS[(i+1) % 100], PUBS[(i+1) % 100]),
                 Output(999 - j, PUBS[i], PUBS[i])]
            )
            for inp in txn.inputs:
                inp.signature = sign2(txn.txid, PRIVS[i])
                inp.signature2 = sign2(txn.txid, PRIVS[i])
            txns.append(txn)
    return txns


def genesis_txn():
    outputs = [Output(1000, PUBS[i], PUBS[i]) for i in range(len(PUBS))]
    return Transaction([], outputs)


def genesis_txn_list_batch():
    txns = []
    for j in range(100):
        txns.extend([Transaction([], [Output(1000 - j, PUBS[i], PUBS[i])]) for i
                                     in range(len(PUBS))])
    return txns



#write transacions into file

f = open('txns_2.txt','w+')
txns = [b2hex(t.serialize().get_bytes()) for t in generate_txns_batch_ll()]
for t in txns:
    f.write("%s\n" % t)
f.close()


    # f = open('genesis_1.txt','w')
# txns = [b2hex(t.serialize().get_bytes()) for t in genesis_txn_list_batch()]
# for t in txns:
#     f.write("%s\n" % t)
# f.close()

# f = open('txns_1.txt','w')
# txns = [b2hex(t.serialize().get_bytes()) for t in generate_txns_batch()]
# for t in txns:
#     f.write("%s\n" % t)
# f.close()