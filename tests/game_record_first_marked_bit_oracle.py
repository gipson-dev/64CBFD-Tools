"""Independent first-set-bit reference, live table addresses and original dispatcher."""
from dataclasses import dataclass
from tools.experiments import game_record_first_marked_bit_match as source
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.game_animation_timeline_oracle import signed
from tools.tests.test_game_point_transform_match import put,read
from tools.tests import test_game_actor_burst_consumer_match as faults
RECORD,MASK_TABLE=0x200000,0x90000
@dataclass(frozen=True)
class Case:
 flags:int=128
 mask:int=0x80000000
 delta:int=0
 phase:int=0
 alias:int=0

def quotient(delta):return(abs(delta)//160)*(-1 if delta<0 else 1)
def fixture(c=Case(),base_cell=source.BASE,mask_cell=source.MASKS):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-128,128)}
 record=base_cell-0x4C if c.alias==1 else mask_cell-0x4C if c.alias==3 else RECORD
 table=(record+0x4C if c.alias==2 else MASK_TABLE+0x80 if c.alias==3 else MASK_TABLE)&0xFFFFFFFF
 m[(record+0x4F)&0xFFFFFFFF]=c.flags
 if c.flags&128 or c.alias:
  put(m,base_cell,(record-c.delta)&0xFFFFFFFF);put(m,mask_cell,table)
  put(m,(table+quotient(signed(c.delta & 0xFFFFFFFF))*4)&0xFFFFFFFF,c.mask)
 return m,record

def result(initial,record,base_cell=source.BASE,mask_cell=source.MASKS):
 if not initial[(record+0x4F)&0xFFFFFFFF]&128:return 0
 delta=signed((record-read(initial,base_cell)) & 0xFFFFFFFF);mask=read(initial,(read(initial,mask_cell)+quotient(delta)*4)&0xFFFFFFFF)
 return(mask&-mask).bit_length()-1 if mask else 0

def public(m):return{a:b for a,b in m.items()if not STACK-128<=a<STACK+128}

class FirstBitOracle(TimingOracle):
 def __init__(self,words,memory,c=Case(),entry=source.ENTRY,connected=None,arguments=None,record=RECORD,forced_result=None):
  super().__init__(words,memory,phase=c.phase,entry=entry,arguments=arguments or(record,),connected=connected)
  self.trace=[];self.cut=None;self.access_count=0;self.forced_result=forced_result
 def access(self):
  if self.own_instruction:
   if self.access_count==self.cut:raise faults.AccessBoundary
   self.access_count+=1
 def get(self,address,size):
  v=super().get(address,size)
  if self.own_instruction:self.trace.append(('R',address,size,v))
  return v
 def put(self,address,value,size):
  super().put(address,value,size)
  if self.recording and self.own_instruction:self.trace.append(('W',address,size,value&((1<<(size*8))-1)))
 def record_call(self,target):
  assert target in(source.ENTRY,source.LOOKUP),('Unbounded first-bit helper',hex(target))
  args=self.arguments(1);self.calls.append((target,args));self.events.append(('CALL',target,args))
 def hook(self,target):
  assert target==source.ENTRY and self.forced_result is not None
  self.r[2]=self.forced_result&0xFFFFFFFF

def caller_fixture(rom,selector=1,command=0x17,c=Case(),count=4):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-128,128)}
 put(m,source.BASE,RECORD);put(m,source.MASKS,MASK_TABLE);put(m,source.COUNT,count&0xFFFFFFFF)
 for i in range(4):
  p=RECORD+i*160;m[p+0x72]=i+1;m[p+0x4F]=c.flags;put(m,MASK_TABLE+i*4,c.mask)
 for i,b in enumerate(rom[source.TABLE_ROM:source.TABLE_ROM+68]):m[source.TABLE+i]=b
 # A target route observes only the selector's low byte and returns index|0x2000.
 identity=selector&255;found=identity!=0 and 0<identity<=min(count,4)
 expected=(result(m,RECORD+(identity-1)*160)|0x2000)if found and command==0x17 else 0
 calls=[(source.LOOKUP,(identity,))]
 if found and command==0x17:calls.append((source.ENTRY,(RECORD+(identity-1)*160,)))
 return m,(selector,command,0xABCD1234),expected,calls
