"""Connect the original owner-record dispatcher and its genuine table entry."""
from pathlib import Path
import json,struct,sys
from tools.tests import game_owner_pool_update_151b0b88_oracle as g
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
p=g.p;DISPATCH,FREE,TABLE=0x15149264,0x1516972C,0x8008A4E8
rom=(g.f/'conker/conker.us.bin').read_bytes();elf=(g.f/'conker/build/conker.us.elf').read_bytes()
raw=rom[0x176714:0x1767C8];assert len(raw)==180
at=elf_slot_offset(elf,DISPATCH,180);assert elf[at:at+180]==raw
dispatch=list(struct.unpack('>45I',raw))
table=rom[0x22EFA8:0x22EFF8];assert struct.unpack_from('>I',table,76)[0]==g.ENTRY
assert elf[elf_slot_offset(elf,TABLE,len(table)):][:len(table)]==table

class Oracle(g.Oracle):
 def __init__(self,target,initial,c):
  linked=dict(g.copy_code());linked.update(zip(range(g.ENTRY,g.ENTRY+len(target)*4,4),target))
  g.FactoryOracle.__init__(self,dispatch,initial,c,entry=DISPATCH,s={},arguments=(g.RECORD,),connected=linked)
  self.service=g.Service(self.memory,c);self.saved=tuple(self.r[16:24]);self.saved_fp=tuple(self.f[20:]);self.saved_s8=self.r[30]
  self.boundaries=[];self.frees=[]
 def record_call(self,t):
  if t==g.ENTRY:self.boundaries.append(tuple(self.arguments(1)))
  elif t==FREE:self.frees.append(tuple(self.arguments(1)));self.pending=t,tuple(self.arguments(1))
  else:super().record_call(t)
 def hook(self,t):
  if t!=FREE:return super().hook(t)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi=self.lo=0xDEADBEEF;self.r[2]=0xBAADF00D

def verify(target,c,countdown,lifetime):
 initial=g.fixture(c);initial[g.RECORD+13]=countdown;initial[g.RECORD+16]=255;initial[g.RECORD+17]=19;g.put(initial,g.RECORD+14,lifetime,2)
 for i,b in enumerate(table):initial[TABLE+i]=b
 before=dict(initial)
 if countdown:g.put(before,g.RECORD+14,(lifetime-g.read(before,g.TICKS))&65535,2)
 expected,s=g.reference(before,c)
 frees=[(g.RECORD,)]if g.read(expected,g.RECORD+14,2)&32768 else[]
 machine=Oracle(target,initial,c).run()
 assert machine.boundaries==[(g.RECORD,)]and machine.frees==frees,('boundaries',c,countdown,lifetime,machine.boundaries,machine.frees,frees)
 assert machine.service.calls==s.calls,('calls',c,countdown,lifetime)
 assert g.public(machine.memory,s.outputs)==g.public(expected,s.outputs),('public',c,countdown,lifetime)
 assert tuple(machine.r[16:24])==machine.saved and tuple(machine.f[20:])==machine.saved_fp and machine.r[30]==machine.saved_s8
 return machine

def main(labels=('byte-pre',)):
 reports=[]
 for label,target in g.streams(labels):
  count=0;seen=set()
  for c in g.cases():
   for countdown,lifetime in((0,1),(1,1),(1,0x8000)):
    machine=verify(target,c,countdown,lifetime);seen.update(machine.visits&set(range(DISPATCH,DISPATCH+180,4)));count+=1
  row=dict(stream=label,caller_words=45,covered_caller_words=len(seen),cases=count,table_index=19,real_table_pointer_verified=True,free_provider_modeled=True,all_parent_modes_qualified=False,c_match_credit=0)
  reports.append(row);print(json.dumps(row),flush=True)
 (p/'caller-screen.json').write_text(json.dumps(dict(passes=True,streams=reports),indent=2)+'\n')

 return dict(passes=True,streams=reports)
