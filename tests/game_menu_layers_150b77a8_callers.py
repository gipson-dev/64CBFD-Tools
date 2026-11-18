"""Connect the complete original menu dispatcher, its real switch table and mode8."""
import json,struct
from tools.tests import game_menu_layers_150b77a8_oracle as g
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
DISPATCH,TABLE=0x150B6BC0,0x8009FD00
rom=(g.f/'conker/conker.us.bin').read_bytes();elf=(g.f/'conker/build/conker.us.elf').read_bytes()
raw=rom[0xE4070:0xE4140];assert len(raw)==208 and elf[elf_slot_offset(elf,DISPATCH,208):][:208]==raw
table=rom[0x2447C0:0x2447E8];assert struct.unpack_from('>I',table,7*4)[0]==0x150B6C58
assert elf[elf_slot_offset(elf,TABLE,len(table)):][:len(table)]==table
class Oracle(g.Oracle):
 def __init__(self,target,initial,c):
  connected=dict(zip(range(g.ENTRY,g.ENTRY+len(target)*4,4),target))
  super().__init__(list(struct.unpack('>52I',raw)),initial,c,entry=DISPATCH,connected=connected);self.boundaries=0
 def record_call(self,t):
  if t==g.ENTRY:self.boundaries+=1
  else:super().record_call(t)
def main():
 reports=[]
 for label,words in g.streams():
  count=0;seen=set()
  for c in g.cases():
   initial=g.fixture(c);initial[g.STATE]=8
   for i,b in enumerate(table):initial[TABLE+i]=b
   expected,s=g.reference(initial,c,home=g.STACK+c.phase-24);m=Oracle(words,initial,c).run()
   assert m.boundaries==1 and m.service.calls==s.calls,('calls',c)
   assert g.public(m.memory)==g.public(expected),('memory',c)
   assert tuple(m.r[16:24])+tuple(m.r[28:])==m.saved and tuple(m.f[20:])==m.saved_fp
   seen.update(m.visits&set(range(DISPATCH,DISPATCH+208,4)));count+=1
  row=dict(stream=label,cases=count,caller_words=52,covered_caller_words=len(seen),command=8,original_table_and_full_parent_verified=True,other_commands_qualified=False,c_match_credit=0);reports.append(row);print(json.dumps(row),flush=True)
 report=dict(passes=True,callers=reports);(g.p/'caller-report.json').write_text(json.dumps(report,indent=2)+'\n');return report
if __name__=='__main__':main()
