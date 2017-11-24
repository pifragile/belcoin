import plyvel
from os.path import join, expanduser
from belcoin_node.txnwrapper import TxnWrapper
from tesseract.serialize import SerializationBuffer
from tesseract.util import b2hex


class PendingDB(object):
    def __init__(self, nid):
        self.db = plyvel.DB(join(expanduser('~/.belcoin'), 'db_pend_'+str(nid)),
                            create_if_missing=True)

    def get(self, key, default=None):
        """Get an object from storage in a dictionary-like way."""
        assert isinstance(key, bytes)
        val = self.db.get(key)

        if val is None:
            return default

        return TxnWrapper.unserialize(SerializationBuffer(val))


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

    def __delitem__(self, key):
        assert isinstance(key, bytes)
        self.db.delete(key)