"""Prove three closed integer-temporary renames in the recovered body."""
import json,struct
from tools.experiments import game_packed_motion_1516a648_match as p
from tools.experiments import game_packed_motion_1516a648_match as n
def main():
 raw,refs=p.payload(p.out/"independent-selected.o");normal,nrefs=n.normalize(raw,refs);a=struct.unpack(">73I",raw);b=struct.unpack(">73I",normal);diff={i for i,(x,y)in enumerate(zip(a,b))if x!=y};groups=[(47,50,11,12),(54,57,12,13),(64,66,14,15)];assert diff=={i for start,end,_,_ in groups for i in(start,end)}
 # Three intervals contain exactly one defining load/move and one use.
 assert (a[47],a[50],b[47],b[50])==(0x860b0010,0x0163082a,0x860c0010,0x0183082a)
 assert (a[54],a[57],b[54],b[57])==(0x860c0018,0x448c2000,0x860d0018,0x448d2000)
 assert (a[64],a[66],b[64],b[66])==(0x440e8000,0xa60e0018,0x440f8000,0xa60f0018)
 # Intervening unchanged words must not touch either member of each live pair.
 def accesses(w):
  op=w>>26;rs=w>>21&31;rt=w>>16&31;rd=w>>11&31;fn=w&63
  if op==0:return ({rs,rt},{rd}) if fn not in (0,2,3,8,9) else ({rt},{rd}) if fn in (0,2,3) else ({rs},set())
  if op in (1,4,5,6,7,20,21,22,23):return ({rs,rt},set())
  if op==17:
   fmt=rs
   return (set(),{rt}) if fmt==0 else ({rt},set()) if fmt==4 else (set(),set())
  if op in (32,33,35,36,37):return ({rs},{rt})
  if op in (40,41,43):return ({rs,rt},set())
  if op in (49,57):return ({rs},set())
  if op in (2,3):return (set(),set())
  return ({rs},{rt})
 for start,end,old,new in groups:
  for i in range(start+1,end):
   assert a[i]==b[i];reads,writes=accesses(a[i]);assert not({old,new}&(reads|writes)),(i,hex(a[i]),old,new,reads,writes)
 # The final renamed use is the jal delay-slot store, executed before the helper.
 assert a[65]>>26==3 and a[66]>>26==41
 result=dict(guard_words=6,closed_temporary_pairs=[{"first":s,"last":e,"raw_register":x,"retail_register":y}for s,e,x,y in groups],intervening_words_checked=True,delay_slot_store_before_call=True,source_installed=False)
 (p.out/"roles.json").write_text(json.dumps(result,indent=2)+"\n");print(json.dumps(result),flush=True);return result
