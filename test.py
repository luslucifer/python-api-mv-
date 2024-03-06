from tinydb import Query,TinyDB

db = TinyDB('idDb.json')
q = Query()

print(db.search((q.id2=='1')&(q.type=='sub')))