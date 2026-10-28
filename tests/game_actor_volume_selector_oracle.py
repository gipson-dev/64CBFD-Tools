"""Actor table selection, unsigned bounds and the real dispatcher call route."""
from dataclasses import dataclass
from tools.experiments import game_actor_volume_selector_match as source
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests import test_game_actor_burst_consumer_match as faults
MASK=0xFFFFFFFF
RECORD,PACKET,PARENT,LOOKUP,JUMPTABLE=0x200000,0x220000,0x150A04D8,0x1505EEF4,0x8009F568
SYMBOLS=dict(D_800D3094=source.COUNT,D_800D3098=source.TABLE,D_800CC2D0=source.ACTORS,func_150A2E4C=source.HELPER)
POINTS=((0,0x80000000,0x3F800000),(0x3FA00000,0xC1900000,0x42C80000),(0x7F800000,0xFF800000,0x7FC12345),(0x7FA12345,1,0xFFC12345))
PARENT_TABLE=(0x150A051C,0x150A06E4,0x150A05C0,0x150A05FC,0x150A063C,0x150A0674,0x150A0674,0x150A070C,0x150A0784,0x150A07AC,0x150A07D0,0x150A08BC,0x150A097C)
@dataclass(frozen=True)
class Case:
 actor:int=0
 selector:int=1
 count:int=1
 flag:int=3
 point:tuple=POINTS[1]
 result:int=0x87654321
 phase:int=0
 record:object=None

def fixture(c=Case(),symbols=SYMBOLS):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-1024,1024)};record=RECORD if c.record is None else c.record
 for i in range(-16,68):m[(record+i)&MASK]=(i*13+0x59)&255
 m[(record+0x15)&MASK]=c.flag
 actor=(symbols['D_800CC2D0']+c.actor*812)&MASK
 for i,v in enumerate(c.point):put(m,(actor+0x14+4*i)&MASK,v)
 put(m,symbols['D_800D3094'],c.count&MASK);put(m,symbols['D_800D3098'],(record-(c.selector&4095)*52)&MASK)
 return m

def reference(initial,c=Case(),symbols=SYMBOLS):
 m=dict(initial);sp=STACK+c.phase;put(m,sp-4,0xDEAD0000);put(m,sp,c.actor&MASK);index=c.selector&4095
 if read(m,symbols['D_800D3094'])<index:return m,1,[]
 record=(read(m,symbols['D_800D3098'])+index*52)&MASK
 if m[(record+0x15)&MASK]&3!=3:return m,0,[]
 actor=(symbols['D_800CC2D0']+read(m,sp)*812)&MASK
 args=(record,*(read(m,(actor+0x14+4*i)&MASK)for i in range(3)))
 for i in range(4):put(m,sp-24+4*i,0xB5000000+i)
 return m,c.result&MASK,[(symbols['func_150A2E4C'],args)]

def public(m):return{a:b for a,b in m.items()if not STACK-1024<=a<STACK+1024}

class ActorVolumeOracle(TimingOracle):
 def __init__(self,words,memory,c=Case(),symbols=SYMBOLS,entry=source.ENTRY,connected=None,arguments=None):
  super().__init__(words,memory,phase=c.phase,entry=entry,arguments=(c.actor&MASK,c.selector&MASK)if arguments is None else arguments,connected=connected)
  self.case,self.symbols=c,symbols;self.trace=[]
 def get(self,address,size):
  value=super().get(address,size)
  if self.own_instruction:self.trace.append(('R',address,size,value))
  return value
 def put(self,address,value,size):
  super().put(address,value,size)
  if self.recording and self.own_instruction:self.trace.append(('W',address,size,value&((1<<(size*8))-1)))
 def record_call(self,target):
  sizes={source.ENTRY:2,self.symbols['func_150A2E4C']:4,LOOKUP:1};assert target in sizes,hex(target)
  args=self.arguments(sizes[target]);self.calls.append((target,args));self.events.append(('CALL',target,args))
 def hook(self,target):
  assert target in(self.symbols['func_150A2E4C'],LOOKUP),hex(target)
  value=(self.symbols['D_800CC2D0']+self.case.actor*812)&MASK if target==LOOKUP else self.case.result&MASK
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo,self.r[2]=0xA5000010,0xA5000011,value
