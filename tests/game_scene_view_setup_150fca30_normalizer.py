"""Pin a direct 100-word match without changing any instruction or binding."""
import hashlib,json
RAW='85c49918aded033be87f792d6948db29d26b8aaff7eb726486bdd9133177950f'
BINDINGS='ebe7a711777ab776c2d6927440a4ff26e40591db4d07ba2e4620c8ea8462d4c7'
def normalize(data,refs):
 assert len(data)==400 and hashlib.sha256(data).hexdigest()==RAW,'Unexpected scene-view instructions'
 assert hashlib.sha256(json.dumps(refs,sort_keys=True).encode()).hexdigest()==BINDINGS,'Unexpected scene-view bindings'
 return data,refs
