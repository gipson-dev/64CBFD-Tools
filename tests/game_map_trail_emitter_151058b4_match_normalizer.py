from pathlib import Path
import json,hashlib,struct
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
SPEC=json.loads((Path(__file__).resolve().parents[1]/'experiments/game_map_trail_emitter_151058b4_match_manifest.json').read_text())
RAW_SHA='676ad38411e9dcd2c89753905e5f5262d28dee85c7a80920445b217f11bc134a'
ORDER={0xB4:0x17C,0x16C:0x184,0x170:0x188,0x178:0x190,0x17C:0x170,0x184:0x178,0x188:0xB4,0x190:0x16C}
def normalize(raw,refs):
 assert len(raw)==788 and hashlib.sha256(raw).hexdigest()==RAW_SHA
 assert json.loads(json.dumps(refs))==SPEC['refs']
 words=list(struct.unpack('>197I',raw));out=words[:];moved={};stack=[]
 for i,w in enumerate(words):
  op,rs,rt=w>>26,w>>21&31,w>>16&31;off=w&65535
  if i in(0,196):
   assert w==(0x27BDFF08 if i==0 else 0x27BD00F8);out[i]=(w&0xFFFF0000)|(((-240 if i==0 else 240))&65535);stack.append(i*4);continue
  if rs!=29 or op in(0,17):continue
  assert op in(9,32,33,35,36,37,40,41,43,49,53,57,61),(i,hex(w))
  assert not 0x78<=off<0x90,('gap access',i,off)
  if off>=0x90:
   assert 0x90<=off<=0xEC and not refs.get(i*4)
   out[i]=(w&0xFFFF0000)|(off-8);stack.append(i*4)
  else:assert off<=0x74
 for dest,origin in ORDER.items():out[dest//4]=out[origin//4]if origin not in ORDER else words[origin//4]
 for offset,rs in refs.items():
  dest=next((to for to,old in ORDER.items()if old==offset),offset);assert dest not in moved;moved[dest]=rs
 assert len(set(ORDER))==len(set(ORDER.values()))==8 and set(ORDER)==set(ORDER.values())
 assert words[0x1C4//4]==out[0x1C4//4]==0x0007000D
 return struct.pack('>197I',*out),moved,stack
