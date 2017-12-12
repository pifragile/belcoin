from tesseract.generated.node_interface_pb2_grpc import NodeInterfaceServicer
from tesseract.generated.node_interface_pb2 import GetTXResponse, \
    GetUTXOsResponse, SendTXResponse, UTXO

from tesseract.util import hex2b, b2hex
from tesseract.serialize import SerializationBuffer
from belcoin_node.txnwrapper import TxnWrapper
from belcoin_node.config import TIME_MULTIPLIER

class GRPCInterface(NodeInterfaceServicer):
    def __init__(self, node):
        super(GRPCInterface, self).__init__()
        self.node = node

    def GetTX(self, request, context):
        print('GetTX Request...')
        txid = request.txid
        txnw = self.node.storage.db.get(txid)
        if txnw is None:
            res = GetTXResponse()
            res.tx = b'0'
            res.blockheight = 0
            return res
        txnw = TxnWrapper.unserialize(SerializationBuffer(txnw))
        txn = txnw.txn

        res = GetTXResponse()
        res.tx = txn.serialize().get_bytes()
        res.blockheight = int(txnw.timestamp / TIME_MULTIPLIER)
        return res

    def GetUTXOs(self, request, context):
        #print('GetUTXOs Request...')
        res = GetUTXOsResponse()
        reslist = []
        utxos = self.node.storage.utxos_for_pubkey_grpc(request.pubkey)
        for u in utxos:
            o = u[2]
            utxo = UTXO()
            utxo.txid = u[0]
            utxo.index = u[1]
            utxo.amount = o.amount
            utxo.pubkey = o.pubkey
            utxo.pubkey2 =o.pubkey2
            utxo.htlc_timeout = o.htlc_timeout
            utxo.htlc_hashlock = o.htlc_hashlock
            utxo.htlc_pubkey = o.htlc_pubkey
            utxo.blockheight = int(u[3] / TIME_MULTIPLIER)
            reslist.append(utxo)
        res.utxos.extend(reslist)
        return res


    def SendTX(self, request, context):
        print('SendTx...')
        txn = request.tx
        self.node.rpc_server.jsonrpc_puttxn(b2hex(txn))
        return SendTXResponse()

