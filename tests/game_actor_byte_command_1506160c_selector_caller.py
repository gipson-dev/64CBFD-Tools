"""Qualify the explicit byte selector against the complete retail dispatch CFG."""
from pathlib import Path
from dataclasses import dataclass,replace
import itertools,json,struct,sys
from tools.experiments import game_actor_byte_command_1506160c_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests import game_actor_byte_command_1506160c_guest as g
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import symbol_rows
PARENT=0x150771F0;POINTER=0x800D154C;FIRST=0x800D1890;SECOND=0x800D1891;SELECTOR=0x800D1892;MODE=0x800D1893
HELPERS=(0x1502EA60,0x1502EA7C)
@dataclass(frozen=True)
class Case(g.Case):
 outer:int=0
 selector:int=0
class Oracle(g.Oracle):
 def record_call(self,t):
  if t==g.ENTRY:return super().record_call(t)
  assert t in HELPERS;args=tuple(map(g.u32,self.arguments(2)));self.calls.append((t,args));self.events.append(('CALL',t,args))
 def hook(self,t):
  assert t in HELPERS
  self.memory[g.ACTOR+0x65]=0xA0+HELPERS.index(t);self.memory[FIRST]^=0xFF
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.r[2]=0x87654321
def main():
 symbols={n:r[1]for _,n,r,_ in symbol_rows((out/'baseline/conker/build/conker.us.elf').read_bytes())if n}
 raw=bound_blob(*payload(out/'selector-local/candidate.o','func_150771F0'),symbols)
 truth=list(struct.unpack_from('>41I',(root/'conker/conker.us.bin').read_bytes(),0xA46A0))
 count=0;visits=[set(),set()]
 cases=[Case(outer=outer,selector=selector,first=(outer*17+selector)&255,second=(outer*31+selector)&255,phase=phase)
  for outer,selector,phase in itertools.product(range(256),(0,1,255),(0,8))]
 cases +=[Case(outer=outer,selector=selector,first=0xAB,second=0xCD,phase=phase)
  for outer,selector,phase in itertools.product((0,1),range(256),(0,8))]
 for c in cases:
  c=replace(c,command=1 if c.selector else 2,slot=0);pair=[]
  for i,caller in enumerate((raw,truth)):
   memory=g.fixture(c);g.put(memory,POINTER,g.ACTOR)
   for p,v in((FIRST,c.first),(SECOND,c.second),(SELECTOR,c.selector),(MODE,c.outer)):memory[p]=v
   code=dict(zip(range(g.ENTRY,g.ENTRY+432,4),g.streams()[0]));m=Oracle(caller,c,entry=PARENT,connected=code,memory=memory,args=()).run()
   if c.outer:
    target=HELPERS[int(c.selector!=0)];expected=dict(m.initial);expected[g.ACTOR+0x65]=0xA0+HELPERS.index(target);expected[FIRST]^=255
    calls=[(target,(g.ACTOR,c.first))]
   else:expected=g.reference(m.initial,c);calls=[(g.ENTRY,(g.ACTOR,c.command,c.first,c.second,0))]
   assert m.calls==calls and g.public(m.memory)==g.public(expected)
   assert m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:]
   pair.append((g.public(m.memory),m.calls,m.r[16:24],m.r[28:],m.f[20:]));visits[i].update(m.visits)
  assert pair[0]==pair[1];count+=1
 r=dict(cases_per_layout=count,layouts=2,body_words=41,frame=32,executed_words=[sum(PARENT+4*i in s for i in range(41))for s in visits],
  all256_outer_and_selector_bytes=True,connected_command_leaf_words=108,alternate_two_helper_internals_contracted=True,
  saved_ABI_public_memory_and_calls_equal=True,raw_fault_order_and_volatile_register_identity_not_claimed=True,source_installed=packet.installed(),matching_credit=0)
 (out/'selector-caller.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
if __name__=='__main__':main()
