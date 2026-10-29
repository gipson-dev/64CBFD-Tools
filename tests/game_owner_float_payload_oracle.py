"""Owner float payload, original record factory and original byte-copy loop."""
from dataclasses import dataclass,replace
import struct
from tools.experiments import game_owner_float_payload_match as source
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
OWNER,OUTPUT,MARK=0x30000,0x50000,0x70000
FACTORY,COPY,ALLOCATE,ZERO=0x15149130,0x10022EC0,0x15167A68,0x100226F0
WINDOW,WINDOW_WORDS,END=0x15027674,7,0x15029BA4
HELPERS=((FACTORY,0x1765E0,49),(COPY,0x22EC0,11))
u32=lambda n:n&0xFFFFFFFF
signed16=lambda n:((n&65535)^32768)-32768
@dataclass(frozen=True)
class Case:
 owner:int=OWNER
 identity:int=0x87
 lifetime:int=0xABCD8001
 priority:int=0x123400E1
 arg3:int=1
 outcome:int=1
 mutation:int=0
 phase:int=0
 seed:int=0
 first:int=0x3E50E561
 second:int=0x3F526E98
def symbols():return dict(D_800A2684=0x800A2684,D_800A2688=0x800A2688,func_15149130=FACTORY,memcpy=COPY)
def args(c):return tuple(map(u32,(c.owner,c.lifetime,c.priority,c.arg3)))
def fixture(c=Case(),s=None):
 s=symbols()if s is None else s;m={STACK+i:(i*17+c.seed*13+0xA5)&255 for i in range(-2048,2304)}
 for base,n in((OWNER-32,256),(OUTPUT-32,256),(MARK,32)):m.update({base+i:(i*29+c.seed*11+0x5A)&255 for i in range(n)})
 if c.owner:m[c.owner+0x3B]=c.identity&255
 for name,value in(('D_800A2684',c.first),('D_800A2688',c.second)):put(m,s[name],value)
 return m
def data(m,p,n):return bytes(m[p+i]for i in range(n))
def public(m):return{a:b for a,b in m.items()if not STACK-2048<=a<STACK+2304}
def effect(m,c,s,home):
 put(m,MARK,0x13579BDF)
 if c.mutation&1:
  m[c.owner+0x3B]^=0x55;put(m,s['D_800A2684'],0xBF800000);put(m,s['D_800A2688'],0x40000000)
 if c.mutation&2:
  # Guest-only incoming-home mutations must not alter the snapshotted payload.
  for i in range(4):put(m,home+4*i,0xABCDEF00+i)
def initialize(m,c):
 put(m,OUTPUT+14,c.lifetime,2)
 for at,v in((13,1),(16,255),(17,28),(18,255),(19,28)):m[OUTPUT+at]=v
 for i in range(16):m[OUTPUT+20+i]=0
def reference(initial,c=Case(),s=None,connected=False,home=None):
 s=symbols()if s is None else s;m=dict(initial);home=STACK+c.phase if home is None else home;payload=home-24
 if not c.owner:return m,[],0,[]
 put(m,payload,c.owner);m[payload+4]=m[c.owner+0x3B];put(m,payload+8,0);put(m,payload+12,read(m,s['D_800A2684']));put(m,payload+16,read(m,s['D_800A2688']))
 a=(u32(signed16(c.lifetime)),0xFFFFFFFF,28,0xFFFFFFFF,1,28,20,c.priority&255,u32(c.arg3));calls=[(s['func_15149130'],a)]
 if connected:calls.append((ALLOCATE,(35,u32(c.arg3),60,1,c.priority&255,1)))
 effect(m,c,s,home);answer=OUTPUT if c.outcome else 0;observations=[]
 if answer:
  initialize(m,c)
  if connected:calls.append((ZERO,(answer+20,16)))
  a=(answer+40,payload,20);calls.append((s['memcpy'],a));packet=data(m,payload,20);observations.append((packet,a[0],20))
  for i,b in enumerate(packet):m[a[0]+i]=b
 return m,calls,answer,observations
class FactoryOracle(TimingOracle):
 def __init__(self,words,memory,c=Case(),entry=None,s=None,connected=None,arguments=None):
  self.case=c;self.syms=symbols()if s is None else s;self.target_home=STACK+c.phase
  super().__init__(words,memory,phase=c.phase,entry=source.ENTRY if entry is None else entry,arguments=args(c)if arguments is None else arguments,connected=connected)
  self.trace=[];self.all_accesses=0;self.cut=None;self.copy_observations=[]
 def execute(self,word):
  if word>>26!=0x20:return super().execute(word)
  # The original factory reloads signed byte parameters from their homes.
  prior=self.own_instruction;self.own_instruction=True;self.dispatched_word=word
  try:
   offset=((word&65535)^32768)-32768;value=self.get(u32(self.r[word>>21&31]+offset),1);self.r[word>>16&31]=u32((value^128)-128);self.r[0]=0
  finally:self.own_instruction=prior
 def access(self):
  if self.own_instruction:
   if self.all_accesses==self.cut:raise faults.AccessBoundary
   self.all_accesses+=1
 def get(self,p,n):
  v=super().get(p,n)
  if self.own_instruction:self.trace.append(('R',p,n,v))
  return v
 def put(self,p,v,n):
  super().put(p,v,n)
  if self.recording and self.own_instruction:self.trace.append(('W',p,n,v&((1<<(8*n))-1)))
 def record_call(self,t):
  counts={source.ENTRY:4,self.syms['func_15149130']:9,self.syms['memcpy']:3,ALLOCATE:6,ZERO:2};assert t in counts,hex(t)
  a=tuple(map(u32,self.arguments(counts[t])));self.calls.append((t,a));self.events.append(('CALL',t,a))
  if t==self.syms['memcpy']:self.copy_observations.append((data(self.memory,a[1],a[2]),a[0],a[2]))
 def hook(self,t):
  c=self.case;s=self.syms;a=self.calls[-1][1]
  if t in(s['func_15149130'],ALLOCATE):effect(self.memory,c,s,self.target_home)
  if t==s['func_15149130']:
   value=OUTPUT if c.outcome else 0
   if value:initialize(self.memory,replace(c,lifetime=a[0]))
  elif t==ALLOCATE:value=OUTPUT if c.outcome else 0
  elif t==ZERO:
   assert a[1]==16
   for i in range(a[1]):self.memory[a[0]+i]=0
   value=0xDEADBEEF
  else:
   assert t==s['memcpy']and 0<=a[2]<=64,(t,a);copy=data(self.memory,a[1],a[2])
   for i,b in enumerate(copy):self.memory[a[0]+i]=b
   value=a[0]
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(value)
def helper_code(rom):
 result={}
 for entry,offset,n in HELPERS:result.update(zip(range(entry,entry+n*4,4),struct.unpack_from('>%dI'%n,rom,offset)))
 return result
def caller_machine(rom,words,c=Case(),connected=True):
 c=replace(c,lifetime=signed16(c.lifetime),priority=c.priority&255,arg3=1);initial=fixture(c);home=STACK+c.phase
 put(initial,home+0x764,c.owner);put(initial,home+0x662,c.lifetime,2);put(initial,home+0x773,c.priority,1)
 code=helper_code(rom)if connected else{};code.update(zip(range(source.ENTRY,source.ENTRY+4*len(words),4),words));code[END]=0
 body=struct.unpack_from('>7I',rom,WINDOW-0x15000000+0x2D4B0);m=FactoryOracle(body,initial,c,entry=WINDOW,connected=code)
 m.before=m.r[:];m.code=WindowCode(m.code,m);m.code.ends=(END,)
 expected,calls,value,observations=reference(initial,c,connected=connected,home=home)
 return m,(expected,[(source.ENTRY,args(c))]+calls,1,observations)
