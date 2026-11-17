"""Checked private scheduling transformation; independent proof is separate."""
from tools.experiments import game_strip_attach_151ae0e4_recovery as source
def derive(words):
 assert words==source.PIN['bound_source_words'],'source word or binding changed'
 out=words[:];out[46]=0x46062202
 out[69:75]=[words[i]for i in(69,70,72,71,74,73)]+[0]
 for i,w in enumerate(words):
  op,fmt=w>>26,w>>21&31
  if op in(1,4,5,6,7,20,21,22,23)or op==17 and fmt==8:
   target=i+1+(((w&65535)^32768)-32768);ni=i+(i>=75);nt=target+(target>=75)
   out[ni]=w&0xFFFF0000|(nt-ni-1)&65535
 assert len(out)==96
 return out
