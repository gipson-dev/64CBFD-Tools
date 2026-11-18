"""Source-field normalization; no retail replacement-word array is embedded."""
import hashlib,struct
from tools.experiments import game_amplitude_terminal_150b89e0_screen as s

def verify(raw,refs):
 assert len(raw)==1380 and hashlib.sha256(raw).hexdigest()==s.PIN['raw_sha256']
 assert refs=={int(k):[tuple(x)for x in values]for k,values in s.PIN['refs'].items()}

def derive(words,refs=None):
 assert len(words)==345
 if refs is not None:verify(struct.pack('>345I',*words),refs)
 result=[]
 for w in words:
  op,rs,rt=w>>26,w>>21&31,w>>16&31;off=w&65535
  if op==9 and rs==rt==29:
   assert off in(0xfe68,408);w+=8 if off==0xfe68 else-8
  elif rs==29 and op in(9,32,33,35,36,37,40,41,43,49,53,57,61)and off>=96:w=(w&0xffff0000)|(off-(16 if off==108 else 8))
  result.append(w)
 order=list(range(345));order[143:145]=[144,143];order[169:191]=[190,186,187,188,189,*range(169,186)];result=[result[i]for i in order]
 assert result[266]>>26==17 and result[266]>>21&31==16 and result[266]&63==2
 # The source multiply is the same finite product with reversed operands.
 # Exact retail instruction identity restores its hardware operand order too.
 w=result[266];fs,ft=w>>11&31,w>>16&31;assert(fs,ft)==(0,10)
 result[266]=(w&~((31<<11)|(31<<16)))|(ft<<11)|(fs<<16)
 if refs is None:return result
 return result,{4*i:refs[4*old]for i,old in enumerate(order)if 4*old in refs}
