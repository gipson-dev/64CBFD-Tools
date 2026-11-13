from pathlib import Path
from dataclasses import dataclass
import itertools,struct
from tools.tests.game_script_sorted_insert_oracle import Oracle
from tools.tests.game_animation_timeline_oracle import signed
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_view_render_pass_oracle import STACK
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments import game_script_node_acquire_1509b5ac_match as source
from tools.pad_generated_object import parse_object

ROOT,OUT=source.ROOT,source.OUT
ENTRY=0x1509B5AC
LOOKUP,CREATE,INSERT,EVENT,ZERO=0x1509B704,0x1509B8FC,0x1509B810,0x150ADAF0,0x100226F0
BITPTR,COLOR=0x800D2E4C,0x8003C8E0
BITS,NODE=0x250000,0x240000

@dataclass(frozen=True)
class Case:
 id:int=19
 force:int=0
 exists:bool=False
 kind:int=0
 early:bool=False
 late:bool=False
 mutation:int=0
 phase:int=0

def fixture(c, node=NODE, bitmap=BITS):
 sp=STACK+c.phase
 m={sp+i:(i*17+0xA5)&255 for i in range(-256,256)}
 for a in range(node-16,node+96):m[a]=(a*13+0xB5)&255
 put(m,node,c.kind,2);put(m,node+6,8,2);put(m,node+10,32,2)
 put(m,BITPTR,bitmap);put(m,COLOR,0x12345678)
 for at in (bitmap+(signed(c.id)>>3),bitmap+((c.kind&1023)>>3),bitmap+(((c.kind^0x401)&1023)>>3)):
  m[at]=0
 if c.early:
  at=bitmap+(signed(c.id)>>3);m[at]|=1<<(c.id&7)
 if c.late:
  key=(c.kind^(0x401 if c.mutation&1 else 0))&1023;at=bitmap+(key>>3);m[at]|=1<<(key&7)
 return m

class Loader(Oracle):
 def __init__(self,words,m,c,node=NODE):
  self.case=c;self.node=node
  super().__init__(words,m,node,c.phase,ENTRY)
  self.r[4]=c.id&0xFFFFFFFF;self.r[5]=c.force&0xFFFFFFFF
 def record_call(self,t):
  assert t in (LOOKUP,CREATE,INSERT,EVENT,ZERO),hex(t)
  args=tuple(self.arguments(2 if t in (EVENT,ZERO) else 1))
  self.calls.append((t,args));self.events.append(('CALL',t,args))
 def hook(self,t):
  c=self.case
  args=self.calls[-1][1]
  if t==LOOKUP:value=self.node if c.exists else 0
  elif t==CREATE:value=self.node
  else:value=0xDEADBEEF
  if t==INSERT and c.mutation&1:self.put(self.node,read(self.memory,self.node,2)^0x401,2)
  if t==EVENT:
   assert read(self.memory,COLOR)==0x06000000
   if c.mutation&2:self.put(self.node,read(self.memory,self.node,2)^0x400,2)
   if c.mutation&4:self.put(STACK+c.phase+4,0 if c.force else 1,4)
  if t==ZERO:
   for i in range(args[1]):self.put(args[0]+i,0,1)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011
  self.r[2]=value

def reference(initial,c,node=NODE):
 m=dict(initial);calls=[];id32=signed(c.id);short=((c.id&65535)^0x8000)-0x8000
 calls.append((LOOKUP,(short&0xFFFFFFFF,)))
 found=node if c.exists else 0
 bitmap=read(m,BITPTR)
 if not c.force and m[bitmap+(id32>>3)]&(1<<(id32&7)):
  return m,calls,0
 if not found:
  calls.append((CREATE,(short&0xFFFFFFFF,)));calls.append((INSERT,(node,)))
  if c.mutation&1:put(m,node,read(m,node,2)^0x401,2)
  flags=read(m,node,2);key=flags&1023
  if not (m[bitmap+(key>>3)]&(1<<(key&7))):
   put(m,COLOR,0x06000000);calls.append((EVENT,(node,0)))
   if c.mutation&2:put(m,node,read(m,node,2)^0x400,2)
   put(m,COLOR,0);flags=read(m,node,2)
  force=(0 if c.force else 1) if (c.mutation&4 and calls[-1][0]==EVENT) else c.force
  if not force or flags&0x400:put(m,node,flags|0x4000,2)
 elif c.force:
  flags=read(m,node,2)
  if flags&0x1000 and not flags&0x800:
   address=node+read(m,node+10,2);size=read(m,node+6,2);calls.append((ZERO,(address,size)))
   for i in range(size):m[address+i]=0
 return m,calls,node

def public(memory):return {a:b for a,b in memory.items() if not STACK-256<=a<STACK+264}

def run():
 _,functions,_=parse_object(OUT/'durable-after.o');offset=functions['func_1509B5AC']['value']
 raw=list(struct.unpack('>86I',sections(OUT/'durable-after.elf')['.text'][1][offset:offset+344]))
 retail=list(struct.unpack_from('>86I',(ROOT/'conker/conker.us.bin').read_bytes(),0xC8A5C))
 total=0;seen=set();paths=set()
 for id,force,exists,kind,early,late,mutation in itertools.product((0,7,215,65536,0xFFFFFFFF),(0,1), (False,True),(0,0x400,0x800,0x1000,0x1400,0x1800,0xFFFF),(False,True),(False,True),(0,1,2,4)):
  c=Case(id,force,exists,kind,early,late,mutation,0);initial=fixture(c);want,calls,result=reference(initial,c)
  models=[Loader(words,initial,c).run() for words in (retail,raw)]
  for model in models:
   assert (public(model.memory),model.calls,model.r[2])==(public(want),calls,result),(c,model.calls,calls,model.r[2],result)
  assert models[0].trace==models[1].trace,(c,'trace')
  assert models[0].memory==models[1].memory,(c,'memory')
  seen.update(p-ENTRY for p in models[0].visits);paths.add(tuple(x[0] for x in calls));total+=1
 print('guest cases',total,'visited',len(seen),'of 86 words','call paths',len(paths),flush=True)
 aliases=0
 for id,force,exists,phase,placement in itertools.product((0,7,16,215),(0,1),(False,True),(0,8),range(4)):
  c=Case(id,force,exists,0x1400,False,False,0,phase);sp=STACK+phase
  node=sp-8 if placement in (0,2) else NODE
  bitmap=sp-8 if placement in (1,2) else sp+40 if placement==3 else BITS
  initial=fixture(c,node,bitmap)
  models=[Loader(words,initial,c,node).run() for words in (retail,raw)]
  assert models[0].memory==models[1].memory and models[0].trace==models[1].trace and models[0].calls==models[1].calls and models[0].r[2]==models[1].r[2],(c,placement)
  aliases+=1
 print('stack alias cases',aliases,flush=True)
 return dict(cases=total,visited=len(seen),call_paths=len(paths),stack_aliases=aliases,missing=[hex(i) for i in range(0,344,4) if i not in seen])
if __name__=='__main__':print(run())
