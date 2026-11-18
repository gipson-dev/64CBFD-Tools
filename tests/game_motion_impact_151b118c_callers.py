"""Connect the genuine callback selector and removal-result window."""
import itertools,json,struct
from tools.tests import game_motion_impact_151b118c_oracle as g
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
WINDOW,END,ROM,TABLE=0x1513D038,0x1513D074,0x16A4E8,0x80089CB8
rom=(g.f/'conker/conker.us.bin').read_bytes();elf=(g.f/'conker/build/conker.us.elf').read_bytes()
raw=rom[ROM:ROM+60];assert elf[elf_slot_offset(elf,WINDOW,len(raw)):][:len(raw)]==raw
table=rom[0x22E778:0x22E778+42*4];assert len(table)==168 and struct.unpack_from('>I',table,16*4)[0]==g.ENTRY
assert elf[elf_slot_offset(elf,TABLE,len(table)):][:len(table)]==table
class Oracle(g.Oracle):
 def __init__(self,target,initial,c,prior):
  connected=dict(zip(range(g.ENTRY,g.ENTRY+len(target)*4,4),target));connected[END]=0
  g.FactoryOracle.__init__(self,list(struct.unpack('>15I',raw)),initial,c,entry=WINDOW,s={},arguments=(g.A,),connected=connected)
  self.service=g.Service(self.memory,c);self.r[2]=16;self.r[7]=prior;self.target_arguments=[]
  self.saved=tuple(self.r[16:24])+tuple(self.r[28:31]);self.saved_fp=tuple(self.f[20:])
  self.code=WindowCode(self.code,self);self.code.ends=(END,)
 def record_call(self,t):
  if t==g.ENTRY:self.target_arguments.append(tuple(self.arguments(1)))
  else:super().record_call(t)
def main():
 reports=[]
 for label,words in g.streams(('phase-s8','blend-oldX-ordered')):
  seen=set();count=0
  for c in g.cases():
   for prior in(0,1):
    initial=g.fixture(c)
    for i,b in enumerate(table):initial[TABLE+i]=b
    expected,s,answer=g.reference(initial,c);m=Oracle(words,initial,c,prior)
    try:m.run()
    except WindowBoundary:pass
    else:raise AssertionError('missing caller continuation')
    assert m.target_arguments==[(g.A,)]and m.service.calls==s.calls,('calls',c,prior)
    assert g.public(m.memory)==g.public(expected),('memory',c,prior)
    assert m.r[4]==g.A and m.r[7]==(prior or not answer) and m.r[2]==initial[g.A+0x71]
    assert tuple(m.r[16:24])+tuple(m.r[28:31])==m.saved and tuple(m.f[20:])==m.saved_fp
    seen.update(m.visits&set(range(WINDOW,END,4)));count+=1
  row=dict(stream=label,cases=count,caller_words=15,caller_coverage=len(seen),table_index=16,real_ROM_ELF_table_and_window=True,all_parent_modes_qualified=False,c_match_credit=0);reports.append(row);print(json.dumps(row),flush=True)
 report=dict(passes=True,streams=reports);(g.p/'caller-report.json').write_text(json.dumps(report,indent=2)+'\n');return report
if __name__=='__main__':main()
