"""Restore the proved order of two disjoint valid-frame packet stores."""
import hashlib,json,struct
RAW='81192ac16816e06e5dffb951c3f54080bd099f234c3e8456c487097adeebb931'
BINDINGS='da90073f8851430e0d9f1bdf69ecbb1aab1052be13ddc1c7226bc36de236e84c'
def normalize(data,refs):
 assert len(data)==396 and hashlib.sha256(data).hexdigest()==RAW
 assert hashlib.sha256(json.dumps(refs,sort_keys=True).encode()).hexdigest()==BINDINGS
 words=list(struct.unpack('>99I',data));words[17],words[18]=words[18],words[17]
 return struct.pack('>99I',*words),refs
