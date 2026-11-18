"""Derive retail words from verified C fields and a proved private-byte mapping.

The manifest stores source indices and FP registers, never a retail word array.
Every source instruction is retained, with no insertion or omission.
"""
from pathlib import Path
import hashlib,json,struct
from tools.experiments import game_surface_impact_150b9ed0_screen as s
from tools.tests.game_surface_impact_150b9ed0_proof import canonical
PIN=json.loads((Path(__file__).parents[1]/'experiments/game_surface_impact_150b9ed0_normalizer_manifest.json').read_text())

def verify(words,refs):
 assert len(words)==291 and hashlib.sha256(struct.pack('>291I',*words)).hexdigest()==s.PIN['raw_sha256']
 assert refs=={int(k):[tuple(v)for v in rows]for k,rows in s.PIN['refs'].items()}

def derive(words,refs=None):
 assert len(words)==291
 if refs is not None:verify(words,refs)
 values=[]
 for w in words:
  op,rs,rt=w>>26,w>>21&31,w>>16&31
  if op==9 and rs==rt==29:
   imm=((w&65535)^32768)-32768;assert abs(imm)==328;w=w&0xffff0000|((344 if imm>0 else -344)&65535)
  elif rs==29 and op in(9,32,33,35,36,37,40,41,43,49,57):
   off=(((w&65535)^32768)-32768)-328;new=canonical(off,True)+344;assert -32768<=new<32768;w=w&0xffff0000|(new&65535)
  values.append(w)
 for index,shift,old,new in PIN['FP_allocation']:
  assert 0x100<=4*index<0x188 and values[index]>>shift&31==old
  op,fmt=values[index]>>26,values[index]>>21&31
  allowed=(16,)if op in(49,57)else(11,)if op==17 and fmt in(0,4)else(6,11,16)if op==17 and fmt==16 else()
  assert shift in allowed and 0<=new<32
  values[index]=values[index]&~(31<<shift)|(new<<shift)
 order=PIN['order'];assert sorted(order)==list(range(291))
 assert all(0x100<=4*i<0x180 and 0x100<=4*j<0x180 for i,j in enumerate(order)if i!=j)
 result=[values[i]for i in order]
 if refs is None:return result
 return result,{4*i:refs[4*j]for i,j in enumerate(order)if 4*j in refs}
