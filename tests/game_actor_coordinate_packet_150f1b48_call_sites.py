"""Inventory aligned direct Game-ROM calls to the packet routine."""
from pathlib import Path
import json,struct
root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-actor-coordinate-packet-150f1b48-durable'
rom=(root/'conker/conker.us.bin').read_bytes();needle=struct.pack('>I',0x0d43c6d2)
hits=[i for i in range(0x2d4b0,0x22d710,4) if rom[i:i+4]==needle]
assert hits==[0x615c4],hits
rows=[{'rom':hex(i),'virtual':hex(0x15000000+i-0x2d4b0)} for i in hits]
(out/'call-sites.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(rows),flush=True)
