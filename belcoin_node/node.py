from belcoin_node.storage import Storage


class Node(object):
    def __init__(self, self_address, partner_addrs):
        self.storage = Storage(self_address, partner_addrs)