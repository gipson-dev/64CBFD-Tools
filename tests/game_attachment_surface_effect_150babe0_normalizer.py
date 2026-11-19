"""Derive four private cache relocations without changing the frame or public objects."""
from pathlib import Path
import hashlib,json,struct
PIN=json.loads((Path(__file__).resolve().parents[1]/'experiments/game_attachment_surface_effect_150babe0_manifest.json').read_text())
def derive(raw,refs,truth,trefs):
 expected={int(k):[tuple(x)for x in v]for k,v in PIN["refs"].items()}
 assert hashlib.sha256(raw).hexdigest()==PIN["raw_sha256"] and refs==expected
 assert len(raw)==len(truth)==1036 and refs==trefs
 w=list(struct.unpack('>259I',raw));tw=struct.unpack('>259I',truth)
 rows=((0x1ac,0x2b,4,0x40,0x44),(0x1b4,0x2b,3,0x44,0x48),(0x3a4,0x23,9,0x44,0x48),(0x3a8,0x23,10,0x40,0x44))
 assert {4*i for i,(x,y)in enumerate(zip(w,tw))if x!=y}=={v[0]for v in rows}
 assert w[0]==0x27bdff30
 # Closed cache accesses and no escaped pointer to either private backing range.
 cache={}
 for i,word in enumerate(w):
  op,rs,rt,imm=word>>26,word>>21&31,word>>16&31,word&65535
  if rs==29 and op in(0x20,0x21,0x23,0x24,0x25,0x28,0x29,0x2b,0x31,0x39)and 0x40<=imm<0x4c:cache[4*i]=word
  if op==9 and rs==29 and rt!=29:assert not 0x40<=imm<0x4c,(i,word)
 assert set(cache)=={v[0]for v in rows}
 for offset,op,reg,old,new in rows:
  assert w[offset//4]==(op<<26)|(29<<21)|(reg<<16)|old
  w[offset//4]=(w[offset//4]&~65535)|new
 assert tuple(w)==tw
 return struct.pack('>259I',*w),rows
