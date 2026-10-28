"""Linked-owner effect: ordered semantic reference and bounded original helper execution."""
from dataclasses import dataclass
from tools.experiments import game_linked_owner_effect_match as source
from tools.tests.test_game_effect_owner_ray import RayOracle
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.game_animation_timeline_oracle import signed
from tools.tests.test_game_point_transform_match import put,read
from tools.tests import test_game_actor_burst_consumer_match as faults
RECORD,OWNER,ALT,EFFECT=0x22000,0x24000,0x26000,0x28000
PREP,ALLOC,COPY,ZERO,RANDOM=0x15191B8C,0x15167A68,0x10022EC0,0x100226F0,0x151D8E20
EXIT_TABLE=0x8008A4C0
@dataclass(frozen=True)
class Case:
 live:int=1
 same:bool=True
 capable:int=1
 flags:int=1
 lifetime:int=127
 byte:int=255
 mode:int=0
 phase:int=0
 alias:int=0
 allocated:bool=True

def half(v):return((v&65535)^32768)-32768
def fixture(c=Case()):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-2048,512)}
 for base in(RECORD,OWNER,ALT,EFFECT):m.update({base+i:(i*13+c.byte)&255 for i in range(-64,0x340)})
 owner=(OWNER,RECORD,RECORD+0x10,RECORD-0x28)[c.alias];put(m,owner,c.live);put(m,owner+0x1D4,c.capable);m[owner+0x3B]=c.byte if c.same else c.byte^128;put(m,RECORD+0x28,owner);m[RECORD+0x2C]=c.byte;m[RECORD+13]=c.flags;m[RECORD+12]=c.byte;m[RECORD+1]=(c.byte*17+3)&255;put(m,RECORD+14,c.lifetime&65535,2);return m

def helper_effect(m,c,sp):
 if c.mode&1:m[RECORD+0x30]^=0x80
 if c.mode&2:put(m,RECORD+0x28,ALT);m[RECORD+12]^=0x55;m[RECORD+1]^=0xAA
 if c.mode&4:m[sp+39]=0
 if c.mode&8:m[sp+39]=0x80

def free_effect(m,record):m[record+0x4A]^=0xA5

def reference(initial,c=Case(),entered=None):
 m=dict(initial);entered=STACK+c.phase if entered is None else entered;owner=read(m,RECORD+0x28);dead=read(m,owner)==0;calls=[];observations=[]
 if not dead:dead=m[RECORD+0x2C]!=m[owner+0x3B]
 if not dead and read(m,owner+0x1D4)!=0:
  dead=True
  if m[RECORD+13]&1:m[RECORD+0x30]|=1;put(m,RECORD+0x2E,read(m,RECORD+14,2),2)
  else:put(m,RECORD+0x2E,300,2)
  calls.append((source.HELPER,(RECORD+0x28,0,m[RECORD+12],m[RECORD+1])));observations.append(bytes(m[RECORD+0x28+i]for i in range(12)));helper_effect(m,c,entered-48)
  if c.mode&4:dead=False
  if c.mode&8:dead=True
 if dead:calls.append((source.FREE,(RECORD,)));free_effect(m,RECORD)
 return m,calls,observations

def public(m):return{a:b for a,b in m.items()if not STACK-2048<=a<STACK+512}

class LinkedOracle(RayOracle):
 def __init__(self,words,memory,c=Case(),entry=source.ENTRY,connected=None,helper=source.HELPER,free=source.FREE,callbacks=()):
  TimingOracle.__init__(self,words,memory,phase=c.phase,entry=entry,arguments=(RECORD,),connected=connected);self.case=c;self.trace=[];self.helper,self.free=helper,free;self.packets=[];self.prep_records=[];self.callback_set=set(callbacks);self.chain=False
 def get(self,address,size):
  value=super().get(address,size)
  if self.own_instruction:self.trace.append(('R',address,size,value))
  return value
 def put(self,address,value,size):
  super().put(address,value,size)
  if self.recording and self.own_instruction:self.trace.append(('W',address,size,value&((1<<(size*8))-1)))
 def record_call(self,target):
  if target==self.helper:n=4;self.packets.append(bytes(self.memory[self.r[4]+i]for i in range(12)))
  elif target in(self.free,source.ENTRY)or target in self.callback_set:n=1
  elif target in(PREP,ZERO):n=2
  elif target==ALLOC:n=6
  elif target==COPY:n=3
  elif target==RANDOM:n=0
  else:raise AssertionError(('Unexpected helper',hex(target)))
  args=self.arguments(n);self.calls.append((target,args));self.events.append(('CALL',target,args))
  if target==PREP:self.prep_records.append(bytes(self.memory[args[0]+i]for i in range(5)))
 def hook(self,target):
  c=self.case;value=0x76543210
  if target==self.helper:helper_effect(self.memory,c,self.r[29])
  elif target==self.free:free_effect(self.memory,self.r[4])
  elif target==PREP:
   assert self.r[5]==14
   if c.mode&1:self.memory[RECORD+0x30]^=0x80
  elif target==ALLOC:
   args=self.arguments(6);assert args[0]==32 and args[2:4]==(0x300,1)and args[5]==1;value=EFFECT if c.allocated else 0
  elif target==COPY:
   dst,src,size=self.arguments(3);assert size==12
   for i in range(size):self.put(dst+i,self.get(src+i,1),1)
   value=dst
  elif target==ZERO:
   dst,size=self.arguments(2);assert size==0x2D0
   for i in range(size):self.put(dst+i,0,1)
  elif target==RANDOM:value=0x12340000|c.byte
  else:assert target in self.callback_set
  for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=value
