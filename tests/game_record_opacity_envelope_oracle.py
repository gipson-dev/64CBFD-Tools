"""Opacity envelope reference and bounded literal MIPS caller execution."""
from dataclasses import dataclass
from tools.experiments import game_record_opacity_envelope_match as source
from tools.tests.test_game_position_byte_attenuation_match import Oracle as DivisionOracle,GuestBreak
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.game_animation_timeline_oracle import signed
from tools.tests.test_game_point_transform_match import put,read
from tools.tests import test_game_actor_burst_consumer_match as faults
RECORD,DESCRIPTOR=0x22000,0x23000
PARENTS={0x15168BAC:14,0x15169988:48,0x15167B44:69,0x15167E0C:195}
@dataclass(frozen=True)
class Case:
 duration:int=100
 fade_in:int=20
 hold:int=30
 fade_out:int=50
 remaining:int=90
 record:int=RECORD
 phase:int=0

def half(v):return((v&65535)^32768)-32768
def byte(v):return((v&255)^128)-128
def quotient(n,d):return (abs(n)//abs(d))*(-1 if (n<0)!=(d<0) else 1)
def fixture(c=Case()):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-768,512)}
 m.update({c.record+i:(i*13+0x59)&255 for i in range(-16,256)})
 put(m,c.record+0x18,((c.fade_in&65535)<<16)|(c.hold&65535));put(m,c.record+0x1C,((c.fade_out&65535)<<16)|(c.duration&65535));put(m,c.record+0x24,c.remaining&65535,2)
 return m

def reference(initial,record=RECORD):
 m=dict(initial);duration=read(m,record+0x1C)&65535;fade_in=half(read(m,record+0x18)>>16);hold=read(m,record+0x18)&65535;fade_out=half(read(m,record+0x1C)>>16);remaining=half(read(m,record+0x24,2));boundary=duration-fade_in
 if remaining>boundary:numerator,denominator=(duration-remaining)*255,fade_in
 elif remaining>boundary-hold:m[record+0x45]=255;return m,None
 else:numerator,denominator=remaining*255,fade_out
 if denominator==0:
  # Literal DIV uses a sentinel solely to reach retail break7. This byte is not a hardware claim.
  m[record+0x45]=7;return m,7
 m[record+0x45]=quotient(numerator,denominator)&255;return m,None

def public(m):return{a:b for a,b in m.items()if not STACK-768<=a<STACK+512}
def free_effect(m,record):m[record+0x4A]^=0xA5

def callback_reference(m,selector):
 calls=[]
 if selector==9:
  calls.append((source.WRAPPER,(RECORD,)));value=4096-half(read(m,RECORD+0x24,2))*4;put(m,RECORD+0x38,value&65535,2);put(m,RECORD+0x3A,read(m,RECORD+0x38,2),2)
 if selector in(9,10):
  calls.append((source.ENTRY,(RECORD,)));m,trap=reference(m);assert trap is None
 return m,calls

def caller_reference(initial,entry,selector):
 m=dict(initial);calls=[]
 if entry==0x15167E0C:
  left=half(half(read(m,RECORD+0x38,2))-signed(read(m,source.TICKS)));put(m,RECORD+0x38,max(left,0),2);assert m[RECORD+0x3A]==0 and m[RECORD+0x2F]==255 and read(m,RECORD+0x38,2)==0
 m,calls=callback_reference(m,selector)
 if entry==0x15169988:
  ticks=signed(read(m,source.TICKS));value=signed((half(read(m,RECORD+0x26,2))+half(read(m,RECORD+0x28,2))*ticks)&0xFFFFFFFF);period=m[RECORD+0x41]*256
  if value>=period:value=signed((value-period)&0xFFFFFFFF)
  elif value<0:value=signed((value+period)&0xFFFFFFFF)
  life=half(read(m,RECORD+0x24,2));put(m,RECORD+0x26,value&65535,2)
  if life:
   left=signed((life-ticks)&0xFFFFFFFF)
   if left<=0:calls.append((source.FREE,(RECORD,)));free_effect(m,RECORD)
   else:put(m,RECORD+0x24,left&65535,2)
 elif entry==0x15167B44:
  delta=byte(m[RECORD+0x22]);count=m[RECORD+0x23];cap=m[DESCRIPTOR+4];phase=half(read(m,RECORD+0x14,2));step=half(read(m,RECORD+0x16,2))
  if delta>0:
   if delta<count:m[RECORD+0x23]=count-delta
   else:put(m,RECORD+0x14,cap*256,2)
  elif delta<0 and quotient(phase,256)>=cap-1 and -delta<count:
   m[RECORD+0x23]=count+delta;put(m,RECORD+0x14,(phase-step)&65535,2)
  put(m,RECORD+0x14,(half(read(m,RECORD+0x14,2))+step)&65535,2)
  if quotient(half(read(m,RECORD+0x14,2)),256)>=cap:calls.append((source.FREE,(RECORD,)));free_effect(m,RECORD)
 elif entry==0x15167E0C:calls.append((source.FREE,(RECORD,)));free_effect(m,RECORD)
 return m,calls

class EnvelopeOracle(DivisionOracle):
 def __init__(self,words,memory,c=Case(),entry=source.ENTRY,connected=None):
  TimingOracle.__init__(self,words,memory,entry=entry,phase=c.phase,arguments=(c.record,),connected=connected);self.trace=[]
 def record_call(self,target):
  assert target in(source.ENTRY,source.WRAPPER,source.FREE),hex(target)
  args=self.arguments(1);self.calls.append((target,args));self.events.append(('CALL',target,args))
 def hook(self,target):
  assert target==source.FREE;free_effect(self.memory,self.r[4])
  for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011
