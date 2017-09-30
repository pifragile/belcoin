from pysyncobj import SyncObj, SyncObjConf, replicated
import plyvel
from os.path import join, expanduser


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