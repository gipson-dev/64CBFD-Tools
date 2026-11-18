"""Checked captures, incoming byte views and neutral scheduling slots."""
from tools.experiments import game_random_trail_151aeab4_recovery as source
def derive(words):
 assert words==source.PIN["bound_source_words"],"source words or bindings changed"

 assert len(words)==120 and words[0]==0x27BDFF68
 out=words[:];moves=[];narrow=[]
 for i,w in enumerate(words):
  op,rs,imm=w>>26,w>>21&31,w&65535
  if rs!=29:continue
  if op in(9,32,33,35,36,37,40,41,43,49,57)and 0x60<=imm<0x98:
   out[i]=(w&0xFFFF0000)|(imm-4);moves.append(i)
  elif op==35 and imm in(0x9C,0xA0):out[i]=(w&0x03FF0000)|(36<<26)|(imm+3);narrow.append(i)
 assert len(moves)>15 and len(narrow)==2
 out=[word for i,w in enumerate(out)for word in([w,0]if i in(18,26,52)else[w])]
 assert len(out)==123
 return out
