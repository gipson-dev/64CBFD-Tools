"""Derive the original layout from source fields and proved private value histories.

The manifest contains source indices and FP register numbers, not retail words.
All434 source instructions are retained. Four operations reconstruct the measured
Z/distance spill histories and the branch-delay pointer setup. The accompanying
finite-value relation has explicit FP-status/NaN/fault-state limits.
"""
from pathlib import Path
import hashlib,json,struct
from tools.experiments import game_target_terminal_150b963c_fitting as s
from tools.tests.game_target_terminal_150b963c_proof import canonical
PIN=json.loads((Path(__file__).parents[1]/'experiments/game_target_terminal_150b963c_normalizer_manifest.json').read_text())

def verify(words,refs):
 assert len(words)==434 and hashlib.sha256(struct.pack('>434I',*words)).hexdigest()==s.PIN['raw_sha256']
 assert refs=={int(k):[tuple(v)for v in rows]for k,rows in s.PIN['refs'].items()}

def derive(words,refs=None):
 assert len(words)==434
 if refs is not None:verify(words,refs)
 values=[]
 for w in words:
  op,rs,rt=w>>26,w>>21&31,w>>16&31
  if op==9 and rs==rt==29:
   imm=((w&65535)^32768)-32768;assert abs(imm)==392;w=(w&0xffff0000)|((-384 if imm<0 else 384)&65535)
  elif rs==29 and op in(9,32,33,35,36,37,40,41,42,43,46,49,53,57,61):
   imm=((w&65535)^32768)-32768;offset=canonical(imm-392,True);assert offset is not None;w=(w&0xffff0000)|((offset+384)&65535)
  values.append(w)
 q=PIN['query_branch'];assert q==138 and values[q]>>26==4 and values[q]>>21&31==2 and values[q]>>16&31==0
 values[q]=(values[q]&0x03ffffff)|(20<<26)
 z,d=PIN['spill_sources'];p=PIN['spray_pointer_source'];assert(z,d,p)==(28,41,259)and words[z]==0xc470001c and words[d]==0x460a4480
 assert values[p]==(9<<26)|(29<<21)|(4<<16)|116
 # Transfer directions, homes and carriers come from the source producers and
 # the private relation. No original replacement instruction is loaded here.
 values.extend([(57<<26)|(29<<21)|((words[z]>>16&31)<<16)|376,
                (49<<26)|(29<<21)|((words[z]>>16&31)<<16)|376,
                (57<<26)|(29<<21)|((words[d]>>6&31)<<16)|380,values[p]])
 for index,entries in PIN['FP_allocation']:
  w=values[index];op,rs=w>>26,w>>21&31
  allowed=(16,)if op in(49,53,57,61)else(11,)if op==17 and rs in(0,4)else(16,11,6)if op==17 and rs in(16,20)else()
  assert allowed and len({at for at,n in entries})==len(entries)
  for at,n in entries:
   assert at in allowed and 0<=n<32;w=(w&~(31<<at))|(n<<at)
  values[index]=w
 order=PIN['order'];assert sorted(order)==list(range(438))and [order[i]for i in PIN['inserted_positions']]==[434,435,436,437]
 inverse={old:new for new,old in enumerate(order)};result=[];bindings={}
 for new,index in enumerate(order):
  w=values[index];op,rs=w>>26,w>>21&31
  if op in(4,5,6,7,20,21,22,23)or op==17 and rs==8:
   assert index<434;target=index+1+((words[index]&65535)^32768)-32768
   if index==253:assert target==258;target=259
   off=inverse[target]-new-1;assert -32768<=off<32768;w=(w&0xffff0000)|(off&65535)
  result.append(w)
  if refs is not None and index*4 in refs:bindings[new*4]=refs[index*4]
 return result if refs is None else(result,bindings)
