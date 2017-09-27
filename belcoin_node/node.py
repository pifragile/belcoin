from belcoin_node.storage import Storage


class Node(object):
    def __init__(self, self_address, partner_addrs, nid):
        self.storage = Storage(self_address, partner_addrs, nid)
        self.nid = nid