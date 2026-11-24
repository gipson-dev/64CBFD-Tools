"""Pin a direct 101-word match without changing any instruction or binding."""
import hashlib,json
RAW='67f6a610147c0874b411280770f5c340029509d643067d47a022f2ca64b76e07'
BINDINGS='f9b0cbe626ccda1c6698d7ac1ed9327eb0d9cabb8f029fda9711c1058da90e9c'
def normalize(data,refs):
 assert len(data)==404 and hashlib.sha256(data).hexdigest()==RAW,'Unexpected menu-transition instructions'
 assert hashlib.sha256(json.dumps(refs,sort_keys=True).encode()).hexdigest()==BINDINGS,'Unexpected menu-transition bindings'
 return data,refs
