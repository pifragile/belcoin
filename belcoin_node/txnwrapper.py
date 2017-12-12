import time
from tesseract.transaction import Transaction
from tesseract.serialize import SerializationBuffer

class TxnWrapper:
    """
    Adds a timestamp and a bitmap which states for each output in txn if it
    is unspent to the transaction.
    """

    def __init__(self, tx, ts, utxos=None):
        self.txn = tx
        self.timestamp = ts

        if utxos is None:
            self.utxos = [True for _ in range(len(self.txn.outputs))]
        else:
            self.utxos = utxos

    @staticmethod
    def unserialize(buf):
        """Create a transaction from a byte stream.

        Args:
            buf: A SerializationBuffer to read from.

        Returns:
            A TxnWrapper
        """
        txn = Transaction.unserialize(buf)
        ts = buf.read_varuint()
        utxos = []
        for _ in range(buf.read_varuint()):
            utxos.append(buf.read_num(1))

        return TxnWrapper(txn,ts,utxos)


    def serialize(self, buf=None):
        """Write a TxnWrapper to a byte stream.

        Args:
            buf: A SerializationBuffer to write to.

        Returns:
            A serialization buffer, either the buf argument or a new buffer.
        """
        if buf is None:
            buf = SerializationBuffer()

        self.txn.serialize(buf)
        buf.write_varuint(self.timestamp)
        buf.write_varuint(len(self.utxos))
        for i in self.utxos:
            buf.write_num(1, i)

        return buf
