"""Actor effects: ordered bounded providers and literal O32/private-memory checks."""
from dataclasses import dataclass
from tools.experiments import game_actor_point_effects_match as source
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_actor_direction_point_oracle import DirectionOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests import test_game_actor_burst_consumer_match as faults
MASK=0xFFFFFFFF
ACTOR=0x220000
SYMBOLS={n:int(n[5:],16)for rows in source.BINDINGS.values()for _,n in rows}
SELECT,QUERY,BASE,SURFACE,FIRST,SECOND=(SYMBOLS[n]for n in('func_15134070','func_151380B4','func_15138120','func_1504715C','func_151382E0','func_15138424'))
PARENT,SETUP,FINAL,TRANSFORM,CHECK=0x15194A68,0x1507DE4C,0x151949F4,0x15143134,0x15145C90
@dataclass(frozen=True)
class Case:
 kind:int=19
 query:int=1
 group:int=0xA71234FF
 context:int=0x81234567
 mode:int=0
 phase:int=0
 seed:int=7
 actor:int=ACTOR

def fixture(c=Case(),symbols=SYMBOLS):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-4096,1024)}
 m.update({c.actor+i:(i*13+c.seed)&255 for i in range(-16,0x340)})
 return m

def fill(m,p,n,seed,salt):
 for i in range(n):m[p+i]=(seed+i*13+salt)&255
def change(m,p,n,salt):
 for i in range(n):m[p+i]^=(salt+i*7)&255
def observation(m,args,second=False):
 p,d=(args[1],args[3])if second else(args[0],args[2])
 return bytes(m[p+i]for i in range(12)),bytes(m[d+i]for i in range(36))
def effect(m,c,sp,ordinal,args):
 p,d=sp-16,sp-56
 if ordinal==1:fill(m,args[2],12,c.seed,21)
 if ordinal==2:
  if c.mode&1:change(m,p,12,0x17);m[c.actor+4]^=0x83
  if c.mode&16:m[sp-17]^=0xFF
 if ordinal==3:
  fill(m,args[0],36,c.seed,79)
  if c.mode&2:change(m,p,12,0x39);m[d+29]^=0xA1
  if c.mode&8:put(m,sp+4,0xDEADBEEF);put(m,sp+8,0x76543210)
 if ordinal==4:
  if c.mode&4:change(m,p,12,0x47);change(m,d,36,0xB3)
  if c.mode&8:put(m,sp+4,0xCAFEBABE);put(m,sp+8,0xFEDCBA98)
 return c.kind&MASK if ordinal==0 else c.query&MASK if ordinal==1 else 0x77770000+ordinal

def reference(initial,c=Case(),symbols=SYMBOLS,sp=None):
 m=dict(initial);sp=STACK+c.phase if sp is None else sp;calls=[];observations=[]
 names=list(SYMBOLS);p,d=sp-16,sp-56
 put(m,sp+4,c.group);put(m,sp+8,c.context)
 def call(i,*args):
  args=tuple(a&MASK for a in args);calls.append((symbols[names[i]],args))
  if i in(4,5):observations.append((symbols[names[i]],observation(m,args,i==5)))
  value=effect(m,c,sp,i,args)
  for j in range(4):put(m,sp-96+4*j,0xB5000000+j)
  return value
 kind=call(0,c.actor)
 if kind!=99:
  available=call(1,c.actor,kind,p);m[sp-17]=available&255
  call(2,c.actor,kind,1)
  if m[sp-17]:
   call(3,d,c.actor)
   call(4,p,kind,d,m[sp+7],read(m,sp+8))
   call(5,c.actor,p,kind,d,m[sp+7],read(m,sp+8))
 return m,calls,observations

def public(m):return{a:b for a,b in m.items()if not STACK-4096<=a<STACK+1024}

class EffectsOracle(TimingOracle):
 def __init__(self,words,memory,c=Case(),symbols=SYMBOLS,entry=source.ENTRY,connected=None,arguments=None):
  super().__init__(words,memory,phase=c.phase,entry=entry,arguments=(c.actor,c.group,c.context)if arguments is None else arguments,connected=connected)
  self.case,self.symbols=c,symbols;self.child_sp=STACK+c.phase;self.trace=[];self.target_entries=[];self.query_point=None
 def get(self,address,size):
  value=super().get(address,size)
  if self.own_instruction:self.trace.append(('R',address,size,value))
  return value
 def put(self,address,value,size):
  super().put(address,value,size)
  if self.recording and self.own_instruction:self.trace.append(('W',address,size,value&((1<<(size*8))-1)))
 def execute(self,word):
  if word>>26 in(34,38,42,46):return DirectionOracle.execute(self,word)
  return super().execute(word)
 def record_call(self,target):
  sizes={v:n for v,n in zip(self.symbols.values(),(1,3,3,2,5,6))}|{source.ENTRY:3,SETUP:1,FINAL:3,TRANSFORM:4,CHECK:1}
  assert target in sizes,hex(target);args=self.arguments(sizes[target]);self.calls.append((target,args));self.events.append(('CALL',target,args))
  if target==source.ENTRY:self.child_sp=self.r[29];self.target_entries.append(args)
  if target in(self.symbols['func_151382E0'],self.symbols['func_15138424']):self.observations.append((target,observation(self.memory,args,target==self.symbols['func_15138424'])))
 def hook(self,target):
  args=self.calls[-1][1]
  if target in self.symbols.values():value=effect(self.memory,self.case,self.child_sp,list(self.symbols.values()).index(target),args)
  elif target==TRANSFORM:fill(self.memory,args[1],12,self.case.seed,21);value=0x1234
  elif target==CHECK:value=self.case.query
  else:
   assert target in(SETUP,FINAL);value=0xED000001
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=value&MASK
