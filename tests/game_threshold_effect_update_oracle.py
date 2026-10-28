"""Threshold updates: signed halfwords, wrapped integer scale and bounded float32 semantics."""
from dataclasses import dataclass
from tools.experiments import game_threshold_effect_update_match as source
from tools.tests.test_game_effect_owner_ray import RayOracle
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.game_animation_timeline_oracle import bits,floating,signed
from tools.tests.test_game_point_transform_match import put,read
from tools.tests import test_game_actor_burst_consumer_match as faults
RECORD,CONTEXT,TICKS=0x22000,0x26000,0x800BE9E4
PARENT,NEXT,FREE,EXIT=0x151303EC,0x151A4900,0x1516972C,0x150C1198
TABLE,EXIT_TABLE,TIME=0x80089760,0x80089800,0x800BE9A4
@dataclass(frozen=True)
class Case:
 counter:int=1
 limits:tuple=(10,10,10)
 scales:tuple=(7,3,2)
 ticks:int=2
 floats:tuple=(0x3FA00000,0xC1280000)
 argument:int=CONTEXT
 phase:int=0
 home:int=-1
 clock:int=TICKS

def half(v):return((v&65535)^32768)-32768
def base(c):return RECORD if c.home<0 else STACK+c.phase+4-c.home
def fixture(c=Case()):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-2048,512)};record=base(c)
 for start,size in((record-32,256),(CONTEXT-16,64),(c.clock-8,20)):
  m.update({start+i:(i*13+0xA5)&255 for i in range(size)})
 put(m,record+0x1A,c.counter&65535,2)
 for i,v in enumerate((c.limits[0],c.scales[0],c.limits[1],c.scales[1],c.limits[2],c.scales[2])):put(m,record+0xA8+2*i,v&65535,2)
 for i,v in enumerate(c.floats):put(m,record+0x38+4*i,v)
 put(m,c.clock,c.ticks&0xFFFFFFFF);return m

def reference(initial,c=Case(),record=None,entered=None,next_callback=False,argument=None):
 m=dict(initial);record=base(c)if record is None else record;entered=STACK+c.phase if entered is None else entered
 put(m,entered+4,c.argument if argument is None else argument)
 counter=half(read(m,record+0x1A,2));p=record+0xA8
 if counter<half(read(m,p+4,2)):m[record+0x2B]=(counter*half(read(m,p+6,2)))&255
 if counter<half(read(m,p+8,2)):
  product=(half(read(m,p+10,2))*read(m,c.clock))&0xFFFFFFFF;increment=floating(bits(float(signed(product))))
  for at in(record+0x38,record+0x3C):put(m,at,bits(floating(read(m,at))+increment))
  counter=half(read(m,record+0x1A,2))
 if next_callback:m[record+0x2C]=(counter*half(read(m,p+2,2)))&255
 elif counter<half(read(m,p,2)):
  m[record+0x72]=1;m[record+0x70]=m[record+0x71]=2;m[record+0x2C]=(counter*half(read(m,p+2,2)))&255;put(m,record+0x18,0x5203,2)
 return m

def public(m):return{a:b for a,b in m.items()if not STACK-2048<=a<STACK+512}
def release(m,p):m[p+0x9C]^=0xA5
def exit_effect(m,p):m[p+0x9D]^=0x5A

def parent_reference(initial,c,flags,selector,exit_selector):
 m=dict(initial);p=RECORD;dead=False;calls=[]
 if flags&1:
  counter=(half(read(m,p+0x1A,2))-read(m,c.clock))&65535;put(m,p+0x1A,counter,2);dead=half(counter)<0
 dt=floating(read(m,TIME))
 if flags&2:put(m,p+0x5C,bits(floating(read(m,p+0x5C))+floating(bits(floating(read(m,p+0x64))*dt))))
 if flags&4:
  for pos,vel in((0x40,0x58),(0x44,0x5C),(0x48,0x60)):put(m,p+pos,bits(floating(read(m,p+pos))+floating(bits(floating(read(m,p+vel))*dt))))
 if not dead and selector!=255:
  target=source.ENTRY if selector==0 else NEXT;arg=STACK+c.phase-16;calls.append((target,(p,arg)));m=reference(m,c,p,STACK+c.phase-88,selector==1,arg)
 if dead:
  if exit_selector!=255:calls.append((EXIT,(p,)));exit_effect(m,p)
  calls.append((FREE,(p,)));release(m,p)
 return m,calls

class ThresholdOracle(RayOracle):
 def __init__(self,words,memory,c=Case(),entry=source.ENTRY,connected=None,arguments=None):
  TimingOracle.__init__(self,words,memory,phase=c.phase,entry=entry,arguments=arguments or(base(c),c.argument),connected=connected);self.trace=[];self.case=c
 def get(self,address,size):
  value=super().get(address,size)
  if self.own_instruction:self.trace.append(('R',address,size,value))
  return value
 def put(self,address,value,size):
  super().put(address,value,size)
  if self.recording and self.own_instruction:self.trace.append(('W',address,size,value&((1<<(size*8))-1)))
 def record_call(self,target):
  assert target in(source.ENTRY,NEXT,FREE,EXIT);args=self.arguments(2 if target in(source.ENTRY,NEXT)else 1);self.calls.append((target,args));self.events.append(('CALL',target,args))
 def hook(self,target):
  assert target in(FREE,EXIT);(release if target==FREE else exit_effect)(self.memory,self.r[4])
  for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011
