"""Derive retail layout from cached-column C by address folding and role allocation."""
from pathlib import Path
import hashlib,json,struct
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
SPEC=json.loads((Path(__file__).resolve().parents[1]/'experiments/game_map_chain_search_15105c24_match_manifest.json').read_text())
ORDER=[0,1,5,3,6,7,2,8,9,10,11,12,*range(13,47)]
# Source-index operand roles, recovered from live intervals at each block.
FIELDS={1:dict(rt=7),2:dict(rt=5),5:dict(rs=7,rt=7),6:dict(rt=8),8:dict(rs=5,rt=14,rd=5),9:dict(rs=5,rt=5),10:dict(rd=3),11:dict(rt=5,rd=15),12:dict(rs=15,rd=5),13:dict(rt=3,rd=24),14:dict(rs=24,rt=3,rd=24),15:dict(rt=24,rd=24),16:dict(rs=24,rt=3,rd=24),17:dict(rt=24,rd=24),18:dict(rs=7,rt=24,rd=25),19:dict(rs=25,rt=5,rd=9),20:dict(rs=9,rt=4),21:dict(rs=4),22:dict(rs=3,rt=3),23:dict(rs=4,rt=10),24:dict(rs=8,rt=10),25:dict(rs=4,rt=4),26:dict(rs=4),28:dict(rs=4,rt=4),30:dict(rs=4),31:dict(rs=4,rt=4),32:dict(rs=4),33:dict(rs=4,rt=10),34:dict(rs=3,rt=3),35:dict(rs=3,rt=12),36:dict(rs=12),39:dict(rs=2,rt=2),40:dict(rs=2,rt=13),41:dict(rs=13)}
def normalize(raw,refs):
 if hashlib.sha256(raw).hexdigest()!=SPEC['raw_sha256']or json.loads(json.dumps(refs))!=SPEC['refs']:raise ValueError('Chain-search source words or bindings changed')
 words=list(struct.unpack('>47I',raw));out=[];bindings={};positions={old:new for new,old in enumerate(ORDER)}
 assert len(ORDER)==46 and set(ORDER)==set(range(47))-{4}
 assert words[4]>>26==9 and words[9]>>26==35 and refs[4*4][0][0]=='R_MIPS_LO16'
 for old in ORDER:
  word=words[old]
  for name,value in FIELDS.get(old,{}).items():
   shift={'rs':21,'rt':16,'rd':11}[name];word=(word&~(31<<shift))|(value<<shift)
  if old==9:word=(word&0xFFFF0000)|(words[4]&65535)
  if old in(37,42):
   assert word>>26==21;target=positions[13 if old==37 else 7];at=positions[old]
   word=(word&0x03FF0000)|(5<<26)|((target-at-1)&65535)
  if old in(38,43):
   assert words[old]>>26==0 and words[old]&63==0
   # Retargeting the backedge to its complete header moves its duplicate shift
   # out of the delay slot; the narrowed induction value transfers there instead.
   rs,rd=(12,3)if old==38 else(13,2);word=(rs<<21)|(rd<<11)|37
  out.append(word)
  origin=4*4 if old==9 else old*4
  if origin in refs:bindings[4*positions[old]]=refs[origin]
 assert len(bindings)==len(refs)==4 and words[31]>>26==out[positions[31]]>>26==35
 return struct.pack('>46I',*out),bindings
