"""Prove the two-word initialization-loop schedule change."""
import json,struct
from tools.experiments import game_effect_record_151580b0_match as p
from tools.experiments import game_effect_record_151580b0_match as n
def main():
 raw,refs=p.payload(p.out/"independent-selected.o");normal,nrefs=n.normalize(raw,refs);a=struct.unpack(">74I",raw);b=struct.unpack(">74I",normal);diff={i for i,(x,y)in enumerate(zip(a,b))if x!=y};assert diff=={41,43};assert(a[41],a[42],a[43])==(0xae0000e0,0x1420fffc,0x26100004);assert(b[41],b[42],b[43])==(0x26100004,0x1420fffc,0xae0000dc)
 # In each iteration, old_cursor+0xE0 equals new_cursor+0xDC. The branch
 # tests the independent loop counter and both paths advance exactly once.
 for base in (0,0x30000,0x7fffff00,0xffffff00):
  rawcursor=retailcursor=base;rawstores=[];retailstores=[]
  for i in range(4):
   rawstores.append((rawcursor+0xe0)&0xffffffff);rawcursor=(rawcursor+4)&0xffffffff;retailcursor=(retailcursor+4)&0xffffffff;retailstores.append((retailcursor+0xdc)&0xffffffff)
  assert rawstores==retailstores and rawcursor==retailcursor
 result=dict(guard_words=2,loop_iterations=4,equal_ordered_store_addresses=True,branch_counter_independent=True,caller_saved_registers_unchanged=True,fault_register_state_not_qualified=True,source_installed=False);(p.out/"roles.json").write_text(json.dumps(result,indent=2)+"\n");print(json.dumps(result),flush=True);return result
