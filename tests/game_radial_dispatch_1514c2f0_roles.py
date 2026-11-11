"""Check that the 17 guards form closed register-role permutations."""
import json,struct
from tools.experiments import game_radial_dispatch_1514c2f0_match as p
from tools.experiments import game_radial_dispatch_1514c2f0_match as n
def main():
 raw,refs=p.payload(p.out/'independent-selected.o');retail,_=n.normalize(raw,refs);ws=list(struct.unpack('>96I',raw));target=struct.unpack('>96I',retail)
 def swapfield(word,shift,a,b):
  v=word>>shift&31;return (word&~(31<<shift))|((b if v==a else a if v==b else v)<<shift)
 def fpr(word):
  op=word>>26;fmt=word>>21&31
  if op==17 and fmt in(0,4):return swapfield(word,11,24,28)
  if op==17 and fmt==16:
   for shift in(16,11,6):word=swapfield(word,shift,24,28)
   return word
  if op==57:return swapfield(word,16,24,28)
  raise AssertionError(hex(word))
 def temp(word):
  op=word>>26;mapping={9:11,11:9,10:12}
  for shift in ((21,16,11)if op==0 else(21,16)):
   v=word>>shift&31;word=(word&~(31<<shift))|(mapping.get(v,v)<<shift)
  return word
 assert {ws[i]for i in(1,5,6)}=={target[i]for i in(1,5,6)}
 ws[1],ws[5],ws[6]=ws[5],ws[6],ws[1]
 for i in(8,9,10,50,52,55,56):ws[i]=fpr(ws[i])
 ws[9],ws[10]=ws[10],ws[9]
 assert ws[39]==0x02009025 and target[39]==0x02009025
 assert ws[57]==0xAFB00020 and target[57]==0xAFB20020;ws[57]=target[57]
 for i in(69,71,72,73,74,77):ws[i]=temp(ws[i])
 assert tuple(ws)==target
 r=dict(guard_words=17,callee_saved_float_roles=[24,28],independent_float_save_words_reordered=3,independent_input_moves_reordered=2,loop_temporary_roles={'t1':'t3','t3':'t1','t2':'t4'},callback_angle_uses_equal_s0_s2_after_delay_slot=True,all_words_explained=True,FCSR_and_fault_semantics_not_inferred_from_roles=True);(p.out/'roles.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
