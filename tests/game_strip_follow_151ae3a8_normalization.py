"""Checked schedule derivation; separate instruction-driven relation."""
from tools.experiments import game_strip_follow_151ae3a8_recovery as source
def derive(words):
 assert words==source.PIN["bound_source_words"],"source words or bindings changed"

 assert len(words)==120
 out=words[:]
 for index,before in((89,0x46043080),(93,0x46045200),(101,0x46085300)):
  assert words[index]==before,(index,hex(words[index]));w=out[index];fs,ft=w>>11&31,w>>16&31;out[index]=(w&~((31<<11)|(31<<16)))|(ft<<11)|(fs<<16)
 out[100],out[101]=out[101],out[100]
 assert words[104]==0x46101201 and words[105]==0x460A6300
 out[104],out[105]=out[105],out[104]
 out=out[:99]+[0]+out[99:100]+[0]+out[100:]
 assert len(out)==122
 return out
