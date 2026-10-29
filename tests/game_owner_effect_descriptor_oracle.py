"""Owner notification, descriptor packet and bounded original constructor."""
from dataclasses import dataclass,replace
import struct
from tools.experiments import game_owner_effect_descriptor_match as source
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests import test_game_actor_burst_consumer_match as faults
OWNER,ALTERNATE,OUTPUT,MATRIX=0x28000,0x29000,0x30000,0x38000
NOTIFY,DISPATCH,CREATE,ALLOC,COPY,DELETE,TRANSFORM=0x1516962C,0x1516944C,0x1513418C,0x15167A68,0x10022EC0,0x1516972C,0x15143134
PARENT,PARENT_ROM,FIRST,SECOND=0x15194794,0x1C1C44,0x151B01B8,0x151B09BC
HELPERS=((NOTIFY,0x196ADC,15),(CREATE,0x16163C,76),(COPY,0x22EC0,11))
PADDING=(9,10,11,17,18,19,46,47)
u32=lambda n:n&0xFFFFFFFF
@dataclass(frozen=True)
class Case:
 owner:int=OWNER
 selector:int=0xA5A500E1
 category:int=0x87654321
 identity:int=0x87
 first:int=0x411CCCCD
 second:int=0x3E126E98
 effect:int=0
 outcome:bool=True
 valid:bool=True
 matrix:bool=False
 actor_type:int=0
 allocation_effect:bool=False
 phase:int=0
 state:int=0
 state_effect:bool=False
def symbols():return dict(D_800A9DCC=0x800A9DCC,D_800A9DD0=0x800A9DD0,func_1516962C=NOTIFY,func_1513418C=CREATE)
def data(m,p,n):return bytes(m[p+i]for i in range(n))
def packet(home):return home-52
def args(c):return tuple(map(u32,(c.owner,c.selector,c.category)))
def fixture(c,s=None):
 s=s or symbols();m={STACK+i:(i*17+0xA5)&255 for i in range(-0x1000,0x400)}
 for base in(OWNER,ALTERNATE,OUTPUT,MATRIX):m.update({base+i:(i*13+0x5A)&255 for i in range(-64,0x280)})
 for owner in(OWNER,ALTERNATE):
  put(m,owner,int(c.valid));put(m,owner+0x3B,c.identity^(0x33 if owner==ALTERNATE else 0),1);put(m,owner+4,c.state,1);put(m,owner+0x1D4,MATRIX if c.matrix else 0);put(m,owner+0x74,c.actor_type,1)
 put(m,s['D_800A9DCC'],c.first);put(m,s['D_800A9DD0'],c.second)
 for i in range(5):put(m,0x800A82BC+4*i,0x151947F4)
 return m
def public(m):return {p:v for p,v in m.items()if not STACK-0x1000<=p<STACK+0x400}
def effect(m,c,s,home):
 if c.effect&1:
  put(m,c.owner+0x3B,read(m,c.owner+0x3B,1)^0x55,1);put(m,s['D_800A9DCC'],0x40000000);put(m,s['D_800A9DD0'],0x3F000000)
 if c.effect&2:put(m,home,ALTERNATE)
 if c.effect&4:put(m,home+4,0x12340080);put(m,home+8,0x80000000)
def reference(initial,c,s=None,connected=False,home=None):
 s=s or symbols();home=STACK+c.phase if home is None else home;m=dict(initial);packets=[]
 put(m,home+4,c.selector);put(m,home+8,c.category)
 if not c.owner:return m,[],0,packets
 put(m,home,c.owner);calls=[(s['func_1516962C'],(40,c.owner,22))]
 if connected:calls.append((DISPATCH,(40,home-88,22)))
 effect(m,c,s,home);owner=read(m,home);p=packet(home)
 # Read identity after notification; preserve every untouched representation byte.
 put(m,p,0);put(m,p+4,0);identity=read(m,owner+0x3B,1);f1=read(m,s['D_800A9DCC']);f2=read(m,s['D_800A9DD0'])
 put(m,p+12,owner);put(m,p+8,identity,1);put(m,p+16,1,1)
 for off in(20,24,28):put(m,p+off,0)
 put(m,p+32,f1);put(m,p+36,f2);put(m,p+40,320,2)
 for off,v in((42,6),(43,10),(44,255),(45,9)):put(m,p+off,v,1)
 packets.append(data(m,p,48));selector=read(m,home+7,1);category=read(m,home+8)
 calls.append((s['func_1513418C'],(p,0,selector,category)))
 if not connected:return m,calls,OUTPUT if c.outcome else 0,packets
 calls.append((ALLOC,(40,category,88,1,selector,1)))
 if c.allocation_effect:put(m,owner+0x3B,read(m,owner+0x3B,1)^1,1)
 if not c.outcome:return m,calls,0,packets
 calls.append((COPY,(OUTPUT+16,p,48)))
 for i,b in enumerate(packets[0]):m[OUTPUT+16+i]=b
 if not read(m,owner)or read(m,owner+0x3B,1)!=identity:
  calls.append((DELETE,(OUTPUT,)));return m,calls,0,packets
 matrix=read(m,owner+0x1D4)
 if matrix and read(m,owner+0x74,1)&15!=15:
  calls.append((TRANSFORM,(OUTPUT+0x24,OUTPUT+0x40,matrix+64,OUTPUT)))
  for i in range(3):put(m,OUTPUT+0x40+4*i,0x3F800000+i*0x800000)
 else:put(m,OUTPUT+0x3A,14,1)
 value=floating(f1);put(m,OUTPUT+0x4C,bits(1.0/floating(bits(value+value))));put(m,OUTPUT+0x50,0)
 return m,calls,OUTPUT,packets
class DescriptorOracle(TimingOracle):
 def __init__(self,words,memory,c=Case(),entry=None,s=None,connected=None,parent=False):
  self.case=c;self.syms=s or symbols();self.home=STACK+c.phase-(32 if parent else 0);self.parent=parent
  arguments=(ALTERNATE,c.owner,0xDEADBEEF)if parent else args(c)
  super().__init__(words,memory,phase=c.phase,entry=source.ENTRY if entry is None else entry,arguments=arguments,connected=connected)
  self.trace=[];self.packets=[];self.notifications=[];self.all_accesses=0;self.cut=None
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
  counts={source.ENTRY:3,self.syms['func_1516962C']:3,DISPATCH:3,self.syms['func_1513418C']:4,ALLOC:6,COPY:3,DELETE:1,TRANSFORM:4,FIRST:2,SECOND:5}
  assert t in counts,hex(t);a=tuple(map(u32,self.arguments(counts[t])));self.calls.append((t,a));self.events.append(('CALL',t,a))
  if t==self.syms['func_1513418C']:self.packets.append(data(self.memory,a[0],48))
  if t==DISPATCH:self.notifications.append(data(self.memory,a[1],8))
 def hook(self,t):
  c=self.case;s=self.syms;a=self.calls[-1][1];value=0x87654321
  if t in(s['func_1516962C'],DISPATCH):effect(self.memory,c,s,self.home)
  elif t==s['func_1513418C']:value=OUTPUT if c.outcome else 0
  elif t==ALLOC:
   if c.allocation_effect:
    owner=read(self.memory,packet(self.home)+12);put(self.memory,owner+0x3B,read(self.memory,owner+0x3B,1)^1,1)
   value=OUTPUT if c.outcome else 0
  elif t==COPY:
   assert a[2]==48
   for i,b in enumerate(data(self.memory,a[1],a[2])):self.memory[a[0]+i]=b
   value=a[0]
  elif t==TRANSFORM:
   assert a==(OUTPUT+0x24,OUTPUT+0x40,MATRIX+64,OUTPUT),a
   for i in range(3):put(self.memory,OUTPUT+0x40+4*i,0x3F800000+i*0x800000)
  elif t==SECOND:
   if c.state_effect:put(self.memory,c.owner+4,(c.state+1)&255,1)
  else:assert t in(DELETE,FIRST),hex(t)
  for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo,self.condition=0xA5000010,0xA5000011,True;self.r[2]=u32(value)
def helper_code(rom):
 result={}
 for entry,offset,n in HELPERS:result.update(zip(range(entry,entry+n*4,4),struct.unpack_from('>%dI'%n,rom,offset)))
 return result
def caller_machine(rom,words,c=Case(),connected=True):
 c=replace(c,selector=255,category=1);initial=fixture(c);code=helper_code(rom)if connected else{};code.update(zip(range(source.ENTRY,source.ENTRY+len(words)*4,4),words))
 m=DescriptorOracle(struct.unpack_from('>31I',rom,PARENT_ROM),initial,c,entry=PARENT,connected=code,parent=True)
 expected=dict(initial);state=(c.state+1)&255 if c.state_effect else c.state
 if c.state_effect:put(expected,c.owner+4,state,1)
 prefix=[(FIRST,(ALTERNATE,c.owner)),(SECOND,(ALTERNATE,c.owner,1000,255,0))]
 if state<5:
  expected,calls,value,packets=reference(expected,c,connected=connected,home=STACK+c.phase-32)
  calls=prefix+[(source.ENTRY,args(c))]+calls
 else:calls=prefix;value=0x87654321;packets=[]
 return m,(expected,calls,value,packets)
