"""Type-0x5B point payload: ordered guest homes and bounded provider contracts."""
from dataclasses import dataclass
from tools.experiments import game_type91_point_effect_match as source
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests import test_game_actor_burst_consumer_match as faults
MASK=0xFFFFFFFF
RECORD,INPUT,ALT,HEAD,PACKET=0x200000,0x210000,0x220000,0x230000,0x240000
TABLE=0x80096BE4
SYMBOLS=dict(func_151DC6A0=source.COMPANION,func_15149130=source.FACTORY,memcpy=source.COPY)
POINTS=((0,0x80000000,0x3F800000),(0x3FA00000,0xC1900000,0x42C80000),(1,0x80000001,0x00800000),(0x7F800000,0xFF800000,0x7FC12345))
def half(x):return ((x&65535)^32768)-32768
def list_address(context):return 0x800DCE50+(context&255)*416+35*4

@dataclass(frozen=True)
class Case:
 lifetime:int=300
 companions:int=1
 flag:int=0xAB
 group:int=0x91
 context:int=0
 allocated:bool=True
 mode:int=0
 point:tuple=POINTS[1]
 position:int=INPUT
 record:int=RECORD
 phase:int=0
 oldhead:int=0
 parsed:int=0x12348000

def fixture(c=Case()):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-4096,1024)}
 for base in(RECORD,INPUT,ALT,HEAD,PACKET,c.position,c.record):
  if not STACK-4096<=base<STACK+1024:
   for i in range(-64,128):m[(base+i)&MASK]=(i*13+0x59)&255
 for base in(c.position,ALT):
  for i,v in enumerate(c.point):put(m,base+4*i,v)
 put(m,list_address(c.context),c.oldhead)
 return m

def copy_bytes(m,d,s,n):
 for i in range(n):m[(d+i)&MASK]=m[(s+i)&MASK]
def clobber_homes(m,sp):
 for i in range(4):put(m,sp+4*i,0xB5000000+i)
def companion_effect(m,c,sp,args):
 if c.mode&1:put(m,args[0],0x419C0000)
 if c.mode&2:put(m,sp,ALT)
 if c.mode&4:
  put(m,sp+4,0x12348001);put(m,sp+12,0xAABBCCFE);put(m,sp+16,0x12345680);put(m,sp+20,0x87654321)
def factory_effect(m,c,sp):
 if c.mode&8:put(m,c.position+8,0xC1880000)
 if c.mode&16:
  put(m,sp-8,0x41200000);m[sp-4]=0x56;m[sp-3]=0x12;m[sp-2]=0x34;m[sp-1]=0x78

def reference(initial,c=Case(),symbols=SYMBOLS):
 m=dict(initial);sp=STACK+c.phase;calls=[];packets=[]
 for at,v in((sp+16,c.group),(sp+20,c.context),(sp+8,c.companions),(sp-28,0xDEAD0000),(sp,c.position),(sp+4,c.lifetime),(sp+12,c.flag)):put(m,at,v&MASK)
 if c.companions&255:
  args=(c.position,m[sp+19],read(m,sp+20));calls.append((symbols['func_151DC6A0'],args));companion_effect(m,c,sp,args);clobber_homes(m,sp-72)
 p=read(m,sp);payload=sp-20
 for i in range(3):put(m,payload+4*i,read(m,p+4*i))
 flag=m[sp+15];context=read(m,sp+20);group=m[sp+19];lifetime=half(read(m,sp+4))&MASK
 for at,v in((sp-48,20),(sp-52,0),(sp-56,1),(sp-8,0),(sp-40,context),(sp-44,group)):put(m,at,v)
 m[sp-4]=flag
 calls.append((symbols['func_15149130'],(lifetime,MASK,91,MASK,1,0,20,group,context)))
 factory_effect(m,c,sp);clobber_homes(m,sp-72)
 if c.allocated:
  calls.append((symbols['memcpy'],((c.record+40)&MASK,payload,20)));packets.append(bytes(m[payload+i]for i in range(20)));copy_bytes(m,c.record+40,payload,20);clobber_homes(m,sp-72)
 return m,calls,packets

def public(m):return{a:b for a,b in m.items()if not STACK-4096<=a<STACK+1024}

class PointEffectOracle(TimingOracle):
 def __init__(self,words,memory,c=Case(),symbols=SYMBOLS,entry=source.ENTRY,connected=None,arguments=None):
  args=(c.position,c.lifetime&MASK,c.companions&MASK,c.flag&MASK,c.group&MASK,c.context&MASK)if arguments is None else arguments
  super().__init__(words,memory,phase=c.phase,entry=entry,arguments=args,connected=connected)
  self.case,self.symbols=c,symbols;self.child_sp=STACK+c.phase;self.trace=[];self.copy_packets=[];self.target_entries=[]
 def get(self,address,size):
  v=super().get(address,size)
  if self.own_instruction:self.trace.append(('R',address,size,v))
  return v
 def put(self,address,value,size):
  super().put(address,value,size)
  if self.recording and self.own_instruction:self.trace.append(('W',address,size,value&((1<<(size*8))-1)))
 def execute(self,word):
  if word>>26!=32:return super().execute(word)
  self.own_instruction=True;self.dispatched_word=word
  try:
   address=(self.r[(word>>21)&31]+half(word))&MASK;value=self.get(address,1)
   self.r[(word>>16)&31]=((value^128)-128)&MASK;self.r[0]=0
  finally:self.own_instruction=False
 def record_call(self,target):
  sizes={source.ENTRY:6,self.symbols['func_151DC6A0']:3,self.symbols['func_15149130']:9,self.symbols['memcpy']:3,source.PARSER:11,source.ALLOCATOR:6,source.HEAP:5,source.INITIALIZER:2,source.BZERO:2}
  assert target in sizes,hex(target);args=self.arguments(sizes[target])
  if target==source.ENTRY:self.child_sp=self.r[29];self.target_entries.append(args)
  if target==self.symbols['memcpy']:self.copy_packets.append(bytes(self.memory[args[1]+i]for i in range(args[2])))
  self.calls.append((target,args));self.events.append(('CALL',target,args))
 def hook(self,target):
  c=self.case;args=self.calls[-1][1];result=0x87654321
  if target==self.symbols['func_151DC6A0']:companion_effect(self.memory,c,self.child_sp,args)
  elif target==self.symbols['func_15149130']:factory_effect(self.memory,c,self.child_sp);result=c.record if c.allocated else 0
  elif target==self.symbols['memcpy']:copy_bytes(self.memory,*args);result=args[0]
  elif target==source.HEAP:result=c.record if c.allocated else 0
  elif target==source.PARSER:put(self.memory,args[3],0x12345678);result=c.parsed
  else:raise AssertionError(('unbounded helper',hex(target)))
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo,self.r[2]=0xA5000010,0xA5000011,result&MASK
