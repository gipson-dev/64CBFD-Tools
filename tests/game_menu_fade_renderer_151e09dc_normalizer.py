"""Pin a direct 101-word match without changing any instruction or binding."""
import hashlib,json
RAW='80a09cdad1e1a2aca93255faec3098abe9832b1b7b59ff19e0630f0677c60384'
BINDINGS='6d99c7019d28dfcc97d1d2c80b896bcd20b5c210926d57933765e26155f053d5'
def normalize(data,refs):
 assert len(data)==404 and hashlib.sha256(data).hexdigest()==RAW,'Unexpected menu-fade instructions'
 assert hashlib.sha256(json.dumps(refs,sort_keys=True).encode()).hexdigest()==BINDINGS,'Unexpected menu-fade bindings'
 return data,refs
