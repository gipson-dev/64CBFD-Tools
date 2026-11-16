"""Actual45word parent and slot3 update route; independent expiry slot3 fixtures, with expiry reload/rescue cases."""
from pathlib import Path
from dataclasses import dataclass,replace
import hashlib,importlib.util,json,struct,sys
from tools.experiments import game_spawn_curve_151a1998_recovery as m
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
o=m.OUT;r=m.ROOT
from tools.tests import game_spawn_curve_151a1998_oracle as original_oracle
spec=importlib.util.spec_from_file_location('spawn_curve_parent_oracle',original_oracle.__file__);g=importlib.util.module_from_spec(spec);sys.modules[spec.name]=g;spec.loader.exec_module(g)
PARENT,ROM,TICKS,UPDATES,EXPIRIES,EXPIRE,FREE,MARK=0x15149264,0x176714,0x800BE9E4,0x8008A4E8,0x8008A4C0,0x151A18DC,0x1516972C,0x70000
elf=(r/'conker/build/conker.us.elf').read_bytes();rom=(r/'conker/conker.us.bin').read_bytes();parent=list(struct.unpack_from('>45I',rom,ROM));frame=(-parent[0])&65535
assert tuple(parent)==struct.unpack_from('>45I',elf,elf_slot_offset(elf,PARENT,180))
table=lambda a:struct.unpack_from('>I',elf,elf_slot_offset(elf,a,4))[0]
assert table(UPDATES+12)==g.ENTRY and table(EXPIRIES+12)==EXPIRE

@dataclass(frozen=True)
class Case(g.Case):
 flags:int=1
 life:int=1
 ticks:int=1
 enabled:int=1
 expiry:int=3
 rescue:int=0
 callback_life:object=None
 callback_slot:int=3

original_fixture=g.fixture
def fixture(c):
 mem=original_fixture(c)
 mem[g.INPUT+13]=c.flags;g.put(mem,g.INPUT+14,c.life,2)
 mem[g.INPUT+17]=3 if c.enabled else 255;mem[g.INPUT+16]=c.expiry&255
 g.put(mem,TICKS,c.ticks);g.put(mem,UPDATES+12,g.ENTRY);g.put(mem,EXPIRIES+12,EXPIRE);g.put(mem,MARK,0)
 return mem
g.fixture=fixture
original_mutate=g.mutate
def mutate(mem,c,kind,index,packet=None):
 original_mutate(mem,c,kind,index,packet)
 if kind=='submit'and index==0 and c.callback_life is not None:
  g.put(mem,g.INPUT+14,c.callback_life,2);mem[g.INPUT+16]=c.callback_slot&255
g.mutate=mutate

def reference(c):
 life=g.s16(c.life-c.ticks)if c.flags&1 else c.life
 if c.enabled:
  child=replace(c,phase=c.phase-frame,life=life);mem,calls,packets,curves=g.reference(child);calls=[(g.ENTRY,(g.INPUT,)),*calls]
 else:
  mem=fixture(c);g.put(mem,g.INPUT+14,life,2);calls=[];packets=[];curves=[]
 if g.s16(g.read(mem,g.INPUT+14,2))<0 and mem[g.INPUT+16]!=255:
  assert mem[g.INPUT+16]==3;calls.append((EXPIRE,(g.INPUT,)))
  if c.rescue:g.put(mem,g.INPUT+14,0,2)
 if g.s16(g.read(mem,g.INPUT+14,2))<0:
  calls.append((FREE,(g.INPUT,)));g.put(mem,MARK,0x13579BDF)
 return mem,calls,packets,curves

class Machine(g.Machine):
 def __init__(self,words,c):
  self.ri=self.si=self.fi=self.emits=0;self.packets=[];self.curves=[];self.packet=None
  connected=dict(zip(range(g.ENTRY,g.ENTRY+len(words)*4,4),words))
  g.FactoryOracle.__init__(self,parent,fixture(c),c,entry=PARENT,arguments=(g.INPUT,),connected=connected)
 def record_call(self,t):
  if t in(g.ENTRY,EXPIRE,FREE):
   a=tuple(self.arguments(1));assert a==(g.INPUT,);self.actual_args=a;self.calls.append((t,a));self.events.append(('CALL',t,a));return
  if t in(g.S['func_15167D84'],g.S['memcpy']):
   a=tuple(g.u32(v)for v in self.arguments(6 if t==g.S['func_15167D84']else 3));self.actual_args=a
   home=g.STACK+self.case.phase-frame
   if t==g.S['func_15167D84']:
    assert a[0]==home-60;self.packet=a[0];self.packets.append(g.data(self.memory,a[0],56))
   else:assert a[1]==home-80;self.curves.append(g.data(self.memory,a[1],20))
   self.calls.append((t,a));self.events.append(('CALL',t,a));return
  super().record_call(t)
 def hook(self,t):
  if t not in(EXPIRE,FREE):return super().hook(t)
  if t==EXPIRE and self.case.rescue:g.put(self.memory,g.INPUT+14,0,2)
  if t==FREE:g.put(self.memory,MARK,0x13579BDF)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.r[2]=0xDEADBEEF;self.hi,self.lo=0xA5000010,0xA5000011

def main():
 raw,refs=payload(o/'qualified.o','func_151A1998');syms=g.S
 streams={'retail':list(struct.unpack_from('>295I',rom,0x1CEE48)),'raw':bound_blob(raw,refs,syms)}
 normal,nrefs=payload(o/'layout-fitted.o','func_151A1998');streams['padded']=bound_blob(normal,nrefs,syms)
 cases=[Case(seed=i%8,phase=(i%2)*8,initial_phase=(-1.,0.,1.25,2.75)[i%4],dt=.5,mutation=(i//4)%8,success=i%3,flags=(i//3)%4,life=(-32768,-1,0,1,32767)[i%5],ticks=i%3,enabled=i&1,expiry=3 if i&2 else-1,rescue=bool(i&4),callback_life=(None,-2,0,1)[i//8%4],callback_slot=3 if i&16 else-1)for i in range(256)]
 observed=set();visits={label:set()for label in streams}
 for index,c in enumerate(cases):
  expected,calls,packets,curves=reference(c)
  observed.add((bool(c.enabled),any(t==EXPIRE for t,a in calls),any(t==FREE for t,a in calls)))
  for label,words in streams.items():
   q=Machine(words,c).run();assert q.calls==calls,(index,label,'caller calls',c,q.calls,calls)
   assert q.packets==packets and q.curves==curves,(index,label,'payload',c)
   assert g.public(q.memory)==g.public(expected),(index,label,'public memory',c)
   visits[label].update(pc for pc in q.visits if PARENT<=pc<PARENT+180)
 assert m.check_inputs();report=dict(cases_per_stream=len(cases),streams=list(streams),parent_words_visited={k:len(v)for k,v in visits.items()},observed_update_expiry_free_routes=[list(x)for x in sorted(observed)],actual_table_slot=3,table_pointer_VA=hex(UPDATES+12),parent_frame=frame,post_callback_timer_and_slot_reload=True,expiry_rescue_reload=True,source_installed=m.installed(),c_match_credit=0,scope='bounded actual parent/callback integration; not gameplay reachability')
 (o/'callers.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
