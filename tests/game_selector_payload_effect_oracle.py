"""Selector effect: independent byte reference and bounded retail call execution."""
from dataclasses import dataclass
from tools.experiments import game_selector_payload_effect_match as source
from tools.tests.test_game_effect_owner_ray import RayOracle
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests import test_game_actor_burst_consumer_match as faults
ACTOR,EFFECT,RECORD=0x22000,0x24000,0x26000
FIND,ALLOC=0x151149AC,0x15167A68
@dataclass(frozen=True)
class Case:
 command:int=0x49
 category:int=6
 lookup:int=1
 allocated:bool=True
 seed:int=0
 mode:int=0
 phase:int=0
 alias:bool=False

def fixture(c=Case(),ids=source.IDS,category=source.CATEGORY):
 m={STACK+i:(i*17+c.seed)&255 for i in range(-2048,512)}
 for base in(ACTOR,EFFECT,RECORD):m.update({base+i:(i*13+c.seed)&255 for i in range(-64,512)})
 for i,v in enumerate((7,8,9,8,9,10)):m[ids+i]=v if c.seed==0 else (c.seed+i*71)&255
 put(m,category,c.category&0xFFFFFFFF)
 for i,v in enumerate((-32768,-1,32767)):put(m,RECORD+16+i*2,v&65535,2)
 return m

def public(m):return{a:b for a,b in m.items()if not STACK-2048<=a<STACK+512}

def payload_bytes(c,selector):return bytes((i*29+c.seed+selector)&255 for i in range(24))

def lookup_effect(m,c,pointer,selector,ids,category):
 for i,v in enumerate(payload_bytes(c,selector)):m[pointer+i]=v
 if c.mode&1:put(m,category,0x87654321)
 if c.mode&2:
  for i in range(6):m[ids+i]^=255
 if c.mode&4:m[ACTOR+3]^=0x55

def factory_effect(m,c,payload):
 if c.mode&8:
  for i in range(24):m[payload+i]^=0xA5

def reference(initial,c=Case(),entered=None,ids=source.IDS,category=source.CATEGORY,lookup=source.LOOKUP,factory=source.FACTORY,copy=source.COPY):
 m=dict(initial);entered=STACK+c.phase if entered is None else entered;sp=entered-80;p=sp+48;h=sp+72
 selected=[m[ids+i]for i in range(6)][(3 if read(m,category)==6 else 0)+c.command-0x49]
 calls=[(lookup,(selected,p))];lookup_effect(m,c,p,selected,ids,category);observations=[]
 if c.lookup:
  m[h]=0;m[h+1]=23;put(m,h+2,300,2);m[h+4]=0
  calls.append((factory,(h,ACTOR,24,255,1)));observations.append(bytes(m[h+i]for i in range(6)))
  factory_effect(m,c,p)
  if c.allocated:
   target=ACTOR if c.alias else EFFECT
   calls.append((copy,(target+24,p,24)))
   for i in range(24):m[target+24+i]=m[p+i]
 return m,calls,observations

class SelectorOracle(RayOracle):
 def __init__(self,words,memory,c=Case(),entry=source.ENTRY,connected=None,ids=source.IDS,category=source.CATEGORY,lookup=source.LOOKUP,factory=source.FACTORY,copy=source.COPY,callbacks=()):
  TimingOracle.__init__(self,words,memory,phase=c.phase,entry=entry,arguments=(ACTOR,c.command&0xFFFFFFFF),connected=connected)
  self.case=c;self.trace=[];self.ids=ids;self.category=category;self.lookup=lookup;self.factory=factory;self.copy=copy;self.callbacks=set(callbacks);self.header_observations=[];self.payload_pointer=STACK+c.phase-(24 if entry==source.PARENT else 0)-32
 def get(self,address,size):
  v=super().get(address,size)
  if self.own_instruction:self.trace.append(('R',address,size,v))
  return v
 def put(self,address,value,size):
  super().put(address,value,size)
  if self.recording and self.own_instruction:self.trace.append(('W',address,size,value&((1<<(size*8))-1)))
 def record_call(self,target):
  n={self.lookup:2,self.factory:5,self.copy:3,source.ENTRY:2,FIND:1,ALLOC:6}.get(target,2 if target in self.callbacks else None)
  assert n is not None,('Unbounded helper',hex(target))
  args=self.arguments(n);self.calls.append((target,args));self.events.append(('CALL',target,args))
  if target==self.factory:self.header_observations.append(bytes(self.memory[self.r[4]+i]for i in range(6)))
 def hook(self,target):
  c=self.case;value=0
  if target==self.lookup:
   self.payload_pointer=self.r[5];lookup_effect(self.memory,c,self.r[5],self.r[4],self.ids,self.category);value=c.lookup&0xFFFFFFFF
  elif target==self.factory:
   factory_effect(self.memory,c,self.payload_pointer);value=(ACTOR if c.alias else EFFECT)if c.allocated else 0
  elif target==self.copy:
   a,b,n=self.arguments(3);assert n in(6,24);data=[self.memory[b+i]for i in range(n)]
   for i,v in enumerate(data):self.memory[a+i]=v
   value=a
  elif target==FIND:value=RECORD if c.lookup else 0
  elif target==ALLOC:value=(ACTOR if c.alias else EFFECT)if c.allocated else 0
  else:assert target in self.callbacks
  for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=value
