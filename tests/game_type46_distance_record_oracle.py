"""Type46 record creation: ordered payload copies and original caller/helper execution."""
from dataclasses import dataclass
import math
from tools.experiments import game_type46_distance_record_match as source
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.test_game_point_transform_match import put,read
from tools.tests import test_game_actor_burst_consumer_match as faults
MASK=0xFFFFFFFF
RECORD,ALT,INPUT,INPUT_ALT,ACTOR,HEAD=0x200000,0x210000,0x220000,0x230000,0x240000,0x250000
LIST=0x800DCE50+70*4
SYMBOLS=dict(func_15167A68=source.FACTORY,memcpy=source.COPY,func_15143E64=source.LENGTH)
POINTS=((0,0x80000000,0x3F800000,0,0,0),(0x3FA00000,0xC1900000,0x42C80000,0xBF000000,0x40000000,0x40400000),(1,0x80000001,0x00800000,0,0,0),(0x7F800000,0xFF800000,0x7FC12345,0,0,0))
@dataclass(frozen=True)
class Case:
 extra:int=20
 allocated:bool=True
 mode:int=0
 point:tuple=POINTS[1]
 result:int=0x41280000
 phase:int=0
 record:int=RECORD
 payload:int=INPUT
 oldhead:int=0

def fixture(c=Case()):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-1024,1024)}
 for base in(c.record,ALT,INPUT,INPUT_ALT,ACTOR,HEAD,c.payload):
  for i in range(-16,256):m[(base+i)&MASK]=(i*13+0x59)&255
 for base in(c.payload,INPUT_ALT):
  for i,v in enumerate(c.point):put(m,base+4*i,v)
 for i,v in enumerate(c.point[:3]):put(m,ACTOR+20+4*i,v)
 m[ACTOR+0x3B]=0xA7;put(m,LIST,c.oldhead)
 return m

def copy_bytes(m,d,s,n):
 for i in range(n):m[(d+i)&MASK]=m[(s+i)&MASK]

def factory_effect(m,c,sp):
 if c.mode&1:put(m,c.payload,bits(19.5));m[c.payload+35]=0xF7
 if c.mode&2:put(m,sp,INPUT_ALT)

def copy_effect(m,c,sp):
 if c.mode&4:put(m,sp-4,ALT)
 if c.mode&32:put(m,c.record+24,bits(-17.0))

def length_effect(m,c,sp):
 if c.mode&8:put(m,sp-4,ALT)
 if c.mode&16:m[c.record+48]=0xA7;put(m,c.record+32,bits(3.5))

def clobber_arguments(m,sp):
 for i in range(4):put(m,sp-48+4*i,0xB5000000+i)

def reference(initial,c=Case(),symbols=SYMBOLS):
 m=dict(initial);sp=STACK+c.phase;put(m,sp,c.payload);put(m,sp+4,c.extra&MASK)
 calls=[(symbols['func_15167A68'],(70,0,(c.extra+200)&MASK,1,255,1))];factory_effect(m,c,sp);clobber_arguments(m,sp)
 if not c.allocated:return m,0,calls,[]
 put(m,sp-4,c.record);p=read(m,sp);calls.append((symbols['memcpy'],(c.record+24,p,36)));copy_bytes(m,c.record+24,p,36);copy_effect(m,c,sp);clobber_arguments(m,sp)
 record=read(m,sp-4);delta=tuple(bits(floating(read(m,record+24+4*i))-floating(read(m,record+36+4*i)))for i in range(3))
 calls.append((symbols['func_15143E64'],(sp-16,)));length_effect(m,c,sp);clobber_arguments(m,sp);record=read(m,sp-4)
 put(m,record+192,c.result);put(m,record+16,1);put(m,record+20,0)
 return m,record,calls,[delta]

def public(m):return{a:b for a,b in m.items()if not STACK-1024<=a<STACK+1024}

class DistanceOracle(TimingOracle):
 def __init__(self,words,memory,c=Case(),symbols=SYMBOLS,entry=source.ENTRY,connected=None,arguments=None):
  super().__init__(words,memory,phase=c.phase,entry=entry,arguments=(c.payload,c.extra&MASK)if arguments is None else arguments,connected=connected)
  self.case,self.symbols=c,symbols;self.child_sp=STACK+c.phase;self.trace=[];self.deltas=[];self.copy_packets=[];self.target_entries=[]
 def get(self,address,size):
  value=super().get(address,size)
  if self.own_instruction:self.trace.append(('R',address,size,value))
  return value
 def put(self,address,value,size):
  super().put(address,value,size)
  if self.recording and self.own_instruction:self.trace.append(('W',address,size,value&((1<<(8*size))-1)))
 def execute(self,word):
  if word>>26==17 and(word>>21)&31==16 and word&63==4:
   self.f[(word>>6)&31]=bits(math.sqrt(floating(self.f[(word>>11)&31])));return
  super().execute(word)
 def record_call(self,target):
  sizes={source.ENTRY:2,self.symbols['func_15167A68']:6,self.symbols['memcpy']:3,self.symbols['func_15143E64']:1,source.HEAP:5,source.INITIALIZER:2,source.FINAL:3}
  assert target in sizes,hex(target);args=self.arguments(sizes[target])
  if target==source.ENTRY:self.child_sp=self.r[29];self.target_entries.append(args)
  if target==self.symbols['func_15143E64']:self.deltas.append(tuple(read(self.memory,args[0]+4*i)for i in range(3)))
  if target==self.symbols['memcpy']:self.copy_packets.append(bytes(self.memory[args[1]+i]for i in range(args[2])))
  self.calls.append((target,args));self.events.append(('CALL',target,args))
 def hook(self,target):
  c=self.case;args=self.calls[-1][1];result=0;fresult=None
  if target in(self.symbols['func_15167A68'],source.HEAP):factory_effect(self.memory,c,self.child_sp);result=c.record if c.allocated else 0
  elif target==self.symbols['memcpy']:
   copy_bytes(self.memory,*args);result=args[0]
   if args[2]==36:copy_effect(self.memory,c,self.child_sp)
  elif target==self.symbols['func_15143E64']:length_effect(self.memory,c,self.child_sp);fresult=c.result
  elif target==source.FINAL:result=0xC0DEC0DE
  else:raise AssertionError(('unbounded helper',hex(target)))
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo,self.r[2]=0xA5000010,0xA5000011,result
  if fresult is not None:self.f[0]=fresult
