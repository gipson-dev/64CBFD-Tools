"""Exercise the original script-table caller into each candidate body."""
import itertools,struct
from tools.experiments import game_script_node_acquire_1509b5ac_match as source
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.pad_generated_object import parse_object
from tools.tests.game_script_node_acquire_1509b5ac_guest import ENTRY,Loader,Case,fixture,NODE
from tools.tests.game_script_sorted_insert_oracle import Oracle
from tools.tests.test_game_point_transform_match import put

rom=(source.ROOT/'conker/conker.us.bin').read_bytes();jal=0x0C000000|((ENTRY>>2)&0x03FFFFFF)
sites=[i for i in range(0,len(rom)-3,4) if struct.unpack_from('>I',rom,i)[0]==jal]
assert sites==[0xC89D0,0xCCED8],sites
parent=0x1509B4A0;parent_words=list(struct.unpack_from('>52I',rom,0xC8950))
truth=list(struct.unpack_from('>86I',rom,0xC8A5C))
_,f,_=parse_object(source.OUT/'durable-after.o');pos=f[source.NAME]['value']
raw=list(struct.unpack('>86I',sections(source.OUT/'durable-after.elf')['.text'][1][pos:pos+344]))
data,refs=payload(source.OUT/'durable-padded.o',source.NAME)
addresses={r[1]:r[2][1] for r in symbol_rows((source.ROOT/'conker/build/conker.us.elf').read_bytes())}
padded=list(bound_blob(data,refs,{s:addresses[s] for v in refs.values() for _,s in v}))
init,setup,predicate,finish=0x1509C120,0x15096970,0x1509CBD4,0x1509C3A0
class Parent(Loader):
 def __init__(self,child,initial,case,allowed):
  self.case=case;self.node=NODE;self.allowed=allowed
  Oracle.__init__(self,parent_words,initial,NODE,case.phase,parent,{ENTRY+4*i:w for i,w in enumerate(child)})
  self.r[4]=0x12345678;self.r[5]=case.force
 def record_call(self,t):
  if t==ENTRY or t in (init,setup,predicate,finish):
   args=tuple(self.arguments(2 if t==ENTRY else 1 if t==predicate else 0))
   self.calls.append((t,args));self.events.append(('CALL',t,args))
  else:super().record_call(t)
 def hook(self,t):
  if t not in (init,setup,predicate,finish):return super().hook(t)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011
  self.r[2]=self.allowed if t==predicate else 0xDEADBEEF
count=0
for id,force,exists,allowed,early,phase in itertools.product((0,7,215),(0,1),(False,True),(0,1),(False,True),(0,8)):
 c=Case(id,force,exists,0x1400,early,False,0,phase);initial=fixture(c)
 put(initial,0x800D2F3C,1,1);put(initial,0x800D2F40,0x260000);put(initial,0x260000,id,2)
 models=[Parent(child,initial,c,allowed).run() for child in (truth,raw,padded)]
 for m in models:
  targets=[t for t,args in m.calls];assert targets.count(ENTRY)==allowed
  if allowed:assert next(args for t,args in m.calls if t==ENTRY)==(id,force)
  assert targets[0:3]==[init,setup,predicate] and targets[-1]==finish
 for m in models[1:]:
  assert m.memory==models[0].memory and m.calls==models[0].calls and m.trace==models[0].trace
 count+=1
print(count,'original table-caller cases per body; two aligned JAL callers located',flush=True)
