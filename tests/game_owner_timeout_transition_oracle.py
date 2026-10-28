"""Owner timeout transition: ordered reference and bounded original instruction execution."""
from dataclasses import dataclass
from tools.experiments import game_owner_timeout_transition_match as source
from tools.tests.test_game_effect_owner_ray import RayOracle
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.game_animation_timeline_oracle import signed
from tools.tests.test_game_point_transform_match import put,read
from tools.tests import test_game_actor_burst_consumer_match as faults
RECORD,OWNER,ALT,RESULT=0x22000,0x24000,0x26000,0x28000
EXIT_TABLE=0x8008A4C0
RESET,EFFECT,FACTORY=0x1519E688,0x1519D030,0x151491F4
@dataclass(frozen=True)
class Case:
 live:int=1
 same:bool=True
 state:int=0
 elapsed:int=200
 ticks:int=1
 flags:int=0
 lifetime:int=300
 byte:int=255
 mode:int=0
 phase:int=0
 alias:int=0

def half(v):return((v&65535)^32768)-32768

def fixture(c=Case(),ticks=source.TICKS,slot=source.SLOT):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-2048,512)}
 for base in(RECORD,OWNER,ALT,RESULT):m.update({base+i:(i*13+c.byte)&255 for i in range(-64,0x240)})
 owner=(OWNER,RECORD,RECORD+0x10,RECORD-0x28)[c.alias]
 put(m,owner,c.live);m[owner+0x3B]=c.byte if c.same else c.byte^128;put(m,owner+0x84,c.state,2)
 put(m,RECORD+0x28,owner);m[RECORD+0x2C]=c.byte;put(m,RECORD+0x30,c.elapsed)
 m[RECORD+13]=c.flags;m[RECORD+12]=c.byte;m[RECORD+1]=(c.byte*17+3)&255;put(m,RECORD+14,c.lifetime&65535,2)
 put(m,ticks,c.ticks);put(m,slot,RESULT);return m

def helper_effect(m,c,sp,slot=source.SLOT):
 if c.mode&1:m[RECORD+13]^=0x80;put(m,RECORD+14,123,2)
 if c.mode&2:put(m,RECORD+0x28,ALT);m[RECORD+12]^=0x55;m[RECORD+1]^=0xAA;put(m,RECORD+0x30,0x87654321)
 if c.mode&4:m[sp+35]=0
 if c.mode&8:m[sp+35]=0x80
 if c.mode&16:put(m,slot,ALT)

def free_effect(m,record):m[record+0x4A]^=0xA5

def reference(initial,c=Case(),entered=None,ticks=source.TICKS,slot=source.SLOT):
 m=dict(initial);entered=STACK+c.phase if entered is None else entered
 owner=read(m,RECORD+0x28);retire=read(m,owner)==0;owner=read(m,RECORD+0x28)
 if m[RECORD+0x2C]!=m[owner+0x3B]:retire=True
 calls=[]
 if not retire:
  elapsed=(read(m,RECORD+0x30)+read(m,ticks))&0xFFFFFFFF;put(m,RECORD+0x30,elapsed)
  if read(m,owner+0x84,2)!=0x7C:
   retire=True
   if signed(elapsed)>200:
    calls.append((source.HELPER,(owner,300,m[RECORD+12],m[RECORD+1])))
    helper_effect(m,c,entered-40,slot)
    if c.mode&4:retire=False
    if c.mode&8:retire=True
 if retire:
  put(m,slot,0);flags=m[RECORD+13];put(m,RECORD+14,65535,2);m[RECORD+13]=flags|1
 return m,calls

def public(m):return{a:b for a,b in m.items()if not STACK-2048<=a<STACK+512}

class TimeoutOracle(RayOracle):
 def __init__(self,words,memory,c=Case(),entry=source.ENTRY,connected=None,helper=source.HELPER,callbacks=(),slot=source.SLOT):
  TimingOracle.__init__(self,words,memory,phase=c.phase,entry=entry,arguments=(RECORD,),connected=connected)
  self.case=c;self.trace=[];self.helper=helper;self.callback_set=set(callbacks);self.slot=slot;self.entered=STACK+c.phase-(24 if entry==source.PARENT else 0)
 def get(self,address,size):
  value=super().get(address,size)
  if self.own_instruction:self.trace.append(('R',address,size,value))
  return value
 def put(self,address,value,size):
  super().put(address,value,size)
  if self.recording and self.own_instruction:self.trace.append(('W',address,size,value&((1<<(size*8))-1)))
 def record_call(self,target):
  if target==self.helper:n=4
  elif target in(source.FREE,source.ENTRY)or target in self.callback_set:n=1
  elif target==RESET:n=0
  elif target==EFFECT:n=6
  elif target==FACTORY:n=8
  else:raise AssertionError(('Unexpected helper',hex(target)))
  args=self.arguments(n);self.calls.append((target,args));self.events.append(('CALL',target,args))
 def hook(self,target):
  value=0x76543210
  if target==self.helper:helper_effect(self.memory,self.case,self.entered-40,self.slot)
  elif target==source.FREE:free_effect(self.memory,self.r[4])
  elif target==FACTORY:helper_effect(self.memory,self.case,self.entered-40,self.slot);value=RESULT
  else:assert target in(self.callback_set|{RESET,EFFECT})
  for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=value
