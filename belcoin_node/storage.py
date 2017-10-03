from pysyncobj import SyncObj, SyncObjConf, replicated
import plyvel
from os.path import join, expanduser
from tesseract.transaction import Transaction,Input,Output
from tesseract.serialize import SerializationBuffer
import time
from tesseract.util import b2hex
from tesseract.exceptions import InvalidTransactionError
from tesseract.crypto import verify_sig,NO_HASH

class Storage(SyncObj):
    def __init__(self, self_addr, partner_addrs, nid):
        self.addr = self_addr
        self.nid = nid
        cfg = SyncObjConf(dynamicMembershipChange=True)
        super(Storage, self).__init__(self_addr, partner_addrs, cfg)



        self.db = plyvel.DB(join(expanduser('~/.belcoin'), 'db_'+str(nid)),
                            create_if_missing=True)

    @replicated
    def set(self, key, value):
        print('Node ' +str(self.nid) + ' received ('+key+','+value+') for storage')
        self.db.put(bytes(key, 'utf-8'), bytes(value, 'utf-8'))

    def get(self, key):
        print('Node ' +str(self.nid)+ ' received a request for '+key)
        val = self.db.get(bytes(key, 'utf-8'))
        if val is None:
            return '###NOT FOUND###'
        else:
            return self.db.get(bytes(key, 'utf-8')).decode()

    @replicated
    def verify_and_write_txn(self,addr,buf):
        txn = Transaction.unserialize(SerializationBuffer(buf))
        ts = int(time.time() * 1000000000)


        for inp in txn.inputs:
            if inp.txid == NO_HASH:  # skip dummy inputs
                continue
            try:
                output_txnw = self.db[inp.txid]
                spent_output = output_txnw.txn.outputs[inp.index]
            except KeyError:
                if addr == self.addr:
                    return "Invalid input on transaction %s!" % b2hex(txn.txid)

                raise InvalidTransactionError(
                    "Invalid input on transaction %s!" % b2hex(txn.txid))

            # verify signatures
            if (not verify_sig(txn.txid, spent_output.pubkey,
                               inp.signature) or
                    not verify_sig(txn.txid, spent_output.pubkey2,
                                   inp.signature2)):
                if addr == self.addr:
                    return "Invalid signatures on transaction %s!" % b2hex(
                        txn.txid)

                raise InvalidTransactionError(
                    "Invalid signatures on transaction %s!" % b2hex(
                        txn.txid))

            #check if outputs are unspent
            if output_txnw.utxos[inp.index] != 0:
                if addr == self.addr:
                    return "Transactions %s uses spent outputs!" % b2hex(
                        txn.txid)
                raise InvalidTransactionError(
                    "Transactions %s uses spent outputs!" % b2hex(
                        txn.txid))

            #set all outputs to spent and write txn




    def __getitem__(self, key):
        obj = self.get(key)
        if obj is None:
            raise KeyError('Key %s not found.' % (b2hex(key)))
        return obj

    def __setitem__(self, key, obj):
        assert isinstance(key, bytes)

        self.set(key, obj.serialize_full().get_bytes())

    def __contains__(self, key):
        return self.db.get(key) is not None