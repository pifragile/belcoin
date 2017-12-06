from tesseract.proto3.node_interface_pb2_grpc import NodeInterfaceServicer
from tesseract.proto3.node_interface_pb2 import GetTXResponse, \
    GetUTXOsResponse, SendTXResponse, UTXO

from tesseract.util import hex2b, b2hex
from tesseract.serialize import SerializationBuffer
from belcoin_node.txnwrapper import TxnWrapper


class GRPCInterface(NodeInterfaceServicer):
    def __init__(self, node):
        super(GRPCInterface, self).__init__()
        self.node = node

    def GetTX(self, request, context):
        txid = request.txid
        txnw = self.node.storage.db.get(hex2b(txid))
        if txnw is None:
            return GetTXResponse(b'0', 0)
        txnw = TxnWrapper.unserialize(SerializationBuffer(txnw))
        txn = txnw.txn

        return GetUTXOsResponse(txn.serialize_full(), txnw.timestamp)

    def GetUTXOs(self, request, context):
        res = GetUTXOsResponse()
        utxos = self.node.storage.utxos_for_pubkey_grpc(request.pubkey)
        for u in utxos:
            o = u[2]
            res.utxos.append(UTXO(u[0], u[1], o.amount, o.pubkey, o.pubkey2,
                                  o.htlc_timeout, o.htlc_hashlock,
                                  o.htlc_pubkey, u[3]))
        return res


    def SendTX(self, request, context):
        txn = request.tx
        self.node.rpc_server.jsonrpc_puttxn(b2hex(txn))
        return SendTXResponse()

