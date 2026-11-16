"""Original timed dispatcher, actual slot-1 constructor, and post-call marker."""
from dataclasses import dataclass,replace
import importlib.util,json,struct,sys
from tools.experiments import game_composite_burst_151a3150_recovery as m
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
from tools.tests import game_composite_burst_151a3150_oracle as original
spec=importlib.util.spec_from_file_location('composite_burst_parent_oracle',original.__file__);g=importlib.util.module_from_spec(spec);sys.modules[spec.name]=g;spec.loader.exec_module(g)
PARENT,ROM,TABLE,DISABLE,NEXT,TAIL=0x151A2960,0x1CFE10,0x8008F8E0,0x800BE616,0x151A2F0C,0x1513170C
elf=(m.ROOT/'conker/build/conker.us.elf').read_bytes();rom=(m.ROOT/'conker/conker.us.bin').read_bytes()
parent=list(struct.unpack_from('>45I',rom,ROM));assert tuple(parent)==struct.unpack_from('>45I',elf,elf_slot_offset(elf,PARENT,180))
assert struct.unpack_from('>2I',elf,elf_slot_offset(elf,TABLE,8))==(NEXT,g.ENTRY)
signed16=lambda n:((n&65535)^32768)-32768

@dataclass(frozen=True)
class Case(g.Case):
 timer:int=1
 fade:int=2
 multiplier:int=3
 trigger:int=2
 selector:int=0
 disabled:int=0
 second:int=0x87654321
 pre_faded:bool=False

original_fixture=g.fixture
def fixture(c):
 mem=original_fixture(c)
 for off,value in((0x1A,c.timer),(0xB0,c.fade),(0xB2,c.multiplier),(0xB4,c.trigger)):g.put(mem,g.INPUT+off,value,2)
 mem[g.INPUT+0xB6]=c.selector&255;mem[DISABLE]=c.disabled
 g.put(mem,TABLE,NEXT);g.put(mem,TABLE+4,g.ENTRY);g.put(mem,g.MARK+4,0);g.put(mem,g.MARK+8,0)
 if c.pre_faded and c.timer<c.fade:mem[g.INPUT+0x2C]=(c.timer*c.multiplier)&255
 return mem
g.fixture=fixture

def reference(c):
 mem=fixture(c);calls=[];packets=[]
 if c.timer<c.fade:mem[g.INPUT+0x2C]=(c.timer*c.multiplier)&255
 if not c.disabled and c.trigger!=-1 and c.selector!=-1 and c.timer<=c.trigger:
  if c.selector==1:
   mem,childcalls,packets=g.reference(replace(c,phase=c.phase-32,pre_faded=True));calls=[(g.ENTRY,(g.INPUT,)),*childcalls]
  else:
   assert c.selector==0;calls.append((NEXT,(g.INPUT,)));g.put(mem,g.MARK+4,0x2468ACE0)
  g.put(mem,g.INPUT+0xB4,0xFFFF,2)
 calls.append((TAIL,(g.INPUT,c.second&0xFFFFFFFF)));g.put(mem,g.MARK+8,0x10203040)
 return mem,calls,packets

class Machine(g.Machine):
 def __init__(self,words,c):
  connected=dict(zip(range(g.ENTRY,g.ENTRY+len(words)*4,4),words));self.packets=[]
  g.FactoryOracle.__init__(self,parent,fixture(c),c,entry=PARENT,arguments=(g.INPUT,c.second),connected=connected)
 def record_call(self,target):
  if target in(g.ENTRY,NEXT,TAIL):
   args=tuple(self.arguments(2 if target==TAIL else 1));self.calls.append((target,args));self.events.append(('CALL',target,args));return
  assert target==g.SUBMIT;args=tuple(self.arguments(3));assert args[0]==g.STACK+self.case.phase-32-116
  self.calls.append((target,args));self.events.append(('CALL',target,args));self.packets.append(g.data(self.memory,args[0],116))
 def hook(self,target):
  if target==g.SUBMIT:return super().hook(target)
  assert target in(NEXT,TAIL)
  g.put(self.memory,g.MARK+(4 if target==NEXT else 8),0x2468ACE0 if target==NEXT else 0x10203040)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=0xDEADBEEF

def main():
 m.check_inputs();streams=m.programs();visits={label:set()for label in streams};routes=set()
 corpus=[Case(seed=i,enabled=i&1,mutation=(i>>1)&1,phase=(i&1)*8,timer=(-32768,-1,0,1,32767)[i%5],fade=(-2,0,2,32767)[i%4],multiplier=(-32768,-1,3,255)[i//4%4],trigger=(-1,0,1,32767)[i//8%4],selector=(-1,0,1)[i//3%3],disabled=(i//32)&1,second=(0x87654321+i*0x10203)&0xFFFFFFFF)for i in range(256)]
 for index,c in enumerate(corpus):
  expected,calls,packets=reference(c);routes.add('constructor'if any(t==g.ENTRY for t,a in calls)else'neighbor'if any(t==NEXT for t,a in calls)else'skipped')
  for label,words in streams.items():
   q=Machine(words,c).run();assert q.calls==calls,(index,label,'calls',q.calls,calls)
   assert q.packets==packets,(index,label,'packet');assert g.public(q.memory)==g.public(expected),(index,label,'public memory')
   assert q.r[2]==0xDEADBEEF;visits[label].update(pc for pc in q.visits if PARENT<=pc<PARENT+180)
 assert routes=={'constructor','neighbor','skipped'}and all(len(v)==45 for v in visits.values())
 report=dict(cases_per_stream=len(corpus),streams=list(streams),parent_words_visited={k:len(v)for k,v in visits.items()},actual_slot=1,table_pointer_VA=hex(TABLE+4),parent_frame=32,routes=sorted(routes),post_callback_marker_clear=True,second_argument_preserved=True,neighbor_callback_and_tail_are_opaque=True,source_installed=m.installed(),c_match_credit=0)
 (m.OUT/'callers.json').write_text(json.dumps(report,indent=2)+'\n');m.check_inputs();print(json.dumps(report),flush=True)
if __name__=='__main__':main()
