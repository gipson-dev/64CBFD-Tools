"""Unsigned distance bounds, ordered record reads, sound ABI and original caller."""
from dataclasses import dataclass
from tools.experiments import game_record_range_sound_match as source
from tools.tests.test_game_effect_owner_ray import RayOracle
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests import test_game_actor_burst_consumer_match as faults
RECORD,ALT,PACKET=0x200000,0x210000,0x220000
MASK=0xFFFFFFFF
sign=lambda n,b=16:((n&((1<<b)-1))^(1<<(b-1)))-(1<<(b-1))
@dataclass(frozen=True)
class Case:
 args:tuple=(0x12345678,0x12345681,0xABCD8123,0,300)
 limit:int=500
 mode:int=0
 choice:int=0x87654321
 handle:int=0xFEDC
 alias:object=None
 home:object=None
 phase:int=0

def address(c,table=source.TABLE):return STACK+c.phase+c.home if c.home is not None else table-c.alias if c.alias is not None else RECORD

def fixture(c,table=source.TABLE):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-1024,1024)};record=address(c,table)
 for base in(record,ALT,PACKET):m.update({(base+i)&MASK:(i*13+0x59)&255 for i in range(-16,0x100)})
 for base,values in((record,(0x8123,0x1234,0xABCD,c.limit)),(ALT,(0x1357,0xFFFE,0x8001,0x7FFF))):
  for i,v in enumerate(values):put(m,base+2*i,v&65535,2)
 put(m,table,(record-c.args[3]*52)&MASK)
 for i,v in enumerate(c.args):put(m,STACK+c.phase+4*i,v&MASK)
 return m

def effect(m,c,sp,record,table):
 if c.mode&1:
  for i,v in enumerate((0x7001,0x8002,0x7FFE,7)):put(m,record+i*2,v,2)
  put(m,table,(ALT-c.args[3]*52)&MASK)
 if c.mode&2:put(m,sp+8,0x1234FEDC);put(m,sp+16,0x76543210)
 if c.mode&4:put(m,sp-4,ALT);put(m,sp-8,0xFFFF8003)
 for i in range(4):put(m,sp-56+4*i,0xB5000000+i)

def reference(initial,c,table=source.TABLE,random=source.RANDOM,sound=source.SOUND,chain=False):
 m=dict(initial);sp=STACK+c.phase;first,last,volume,index,distance=c.args
 put(m,sp-12,0xDEAD0000);put(m,sp+4,last&MASK);put(m,sp+8,volume&MASK)
 record=(read(m,table)+index*52)&MASK;limit=sign(read(m,record+6,2));distance=read(m,sp+16)
 if distance>=(limit&MASK):put(m,sp+16,(limit-1)&MASK)
 put(m,sp-4,record);put(m,sp-8,limit&MASK)
 calls=[(random,(first&MASK,(read(m,sp+4)-first+1)&255))]
 effect(m,c,sp,record,table);record=read(m,sp-4);put(m,sp-40,0);limit=read(m,sp-8)
 x=sign(read(m,record,2))&MASK;distance=read(m,sp+16);put(m,sp-36,x)
 y=sign(read(m,record+2,2))&MASK;volume=read(m,sp+10,2);put(m,sp-32,y)
 z=sign(read(m,record+4,2))&MASK;put(m,sp-20,limit);put(m,sp-24,distance);put(m,sp-28,z)
 args=(c.choice&MASK,volume,0,0,0,x,y,z,distance,limit);calls.append((sound,args))
 if chain:calls.append((source.SUBMIT,(0,*args[:5],*(sign(v)&MASK for v in args[5:]))))
 return m,calls

def public(m):return{a:b for a,b in m.items()if not STACK-1024<=a<STACK+1024}

class SoundOracle(RayOracle):
 def __init__(self,words,memory,c=Case(),entry=source.ENTRY,connected=None,table=source.TABLE,random=source.RANDOM,sound=source.SOUND,arguments=None):
  TimingOracle.__init__(self,words,memory,phase=c.phase,entry=entry,arguments=c.args if arguments is None else arguments,connected=connected)
  self.case,self.table,self.random,self.sound=c,table,random,sound;self.child_sp=STACK+c.phase;self.trace=[];self.target_entries=[];self.drop_table=False
 def get(self,address,size):
  value=super().get(address,size)
  if self.own_instruction:self.trace.append(('R',address,size,value))
  return value
 def put(self,address,value,size):
  super().put(address,value,size)
  if self.recording and self.own_instruction:self.trace.append(('W',address,size,value&((1<<(8*size))-1)))
 def record_call(self,target):
  if target==source.ENTRY:self.child_sp=self.r[29];args=self.arguments(5);self.target_entries.append(args)
  else:
   sizes={self.random:2,self.sound:10,source.SUBMIT:11};assert target in sizes,hex(target);args=self.arguments(sizes[target])
  self.calls.append((target,args));self.events.append(('CALL',target,args))
 def hook(self,target):
  assert target in(self.random,self.sound,source.SUBMIT)
  if target==self.random:
   record=read(self.memory,self.child_sp-4);effect(self.memory,self.case,self.child_sp,record,self.table);value=self.case.choice&MASK
   if self.drop_table:
    for i in range(4):self.memory.pop(self.table+i,None)
    for i in range(2):self.memory.pop(record+6+i,None)
  else:
   for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
   value=self.case.handle&65535
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=value
