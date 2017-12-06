import grpc
import time
from tesseract.transaction import Transaction
from tesseract.serialize import SerializationBuffer
from tesseract.generated import node_interface_pb2_grpc
from tesseract.generated.node_interface_pb2 import SendTXRequest,GetTXRequest,\
    GetUTXOsRequest
from belcoin_node.config import BASE_PORT_GRPC
from belcoin_node.util import PUBS
from test import createtxns2

channel = grpc.insecure_channel('localhost:' + str(BASE_PORT_GRPC))
stub = node_interface_pb2_grpc.NodeInterfaceStub(channel)



# for txn in createtxns2.generate_txns():
#     req = SendTXRequest()
#     req.tx = txn.serialize_full().get_bytes()
#     stub.SendTX(req)
#
# time.sleep(20)

# req = GetTXRequest()
# req.txid = createtxns2.generate_txns()[0].txid
# print(Transaction.unserialize_full(SerializationBuffer(stub.GetTX(
#     req).tx)))

req = GetUTXOsRequest()
req.pubkey = PUBS[0]
res = stub.GetUTXOs(req)
for i in res.utxos:
    print(i.index, i.pubkey, i.blockheight)