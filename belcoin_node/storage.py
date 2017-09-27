from pysyncobj import SyncObj, SyncObjConf, replicated


class Storage(SyncObj):
    def __init__(self, self_addr, partner_addrs):
        self.addr = self_addr
        cfg = SyncObjConf(dynamicMembershipChange = True)
        super(Storage, self).__init__(self_addr, partner_addrs, cfg)
        self.__data = {}

    @replicated
    def set(self, key, value):
        print(self.addr + ' received ('+key+','+value+') for storage')
        self.__data[key] = value

    def get(self, key):
        print(self.addr + ' received a request for '+ key)
        return self.__data.get(key, None)