"""Two-vector effect: independent copy/call reference and bounded original providers."""
from dataclasses import dataclass
from tools.experiments import game_two_vector_effect_match as source
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests import test_game_actor_burst_consumer_match as faults
OWNER,OUTPUT,MARK=0x30000,0x70000,0x80000
FACTORY,COPY=0x151602C0,0x10022EC0
PATTERNS=(0,0x80000000,1,0x007FFFFF,0x00800000,0x3F800000,0xBF800000,0x7F7FFFFF,0xFF7FFFFF,0x7F800000,0xFF800000,0x7FC01234,0x7F801234,0xFFFFFFFF,0xA5A5A5A5,0x01234567)
@dataclass(frozen=True)
class Case:
 owner:int=OWNER
 answer:int=OUTPUT
 mode:int=0
 seed:int=0
 phase:int=0
 allocated:bool=True
 alias_output:bool=False

def symbols():return dict(D_800A5970=source.VEC_A,D_800A597C=source.VEC_B,D_800A5E58=source.PARAM,func_15160CDC=source.EFFECT)
def fixture(c=Case(),s=None):
 s=symbols()if s is None else s;m={STACK+i:(i*17+c.seed+0xA5)&255 for i in range(-2048,512)}
 for base,size in((OWNER,1024),(OUTPUT,128),(MARK,32)):
  m.update({base+i:(i*29+c.seed)&255 for i in range(size)})
 values=(0x42500000,0,0x42A00000,0x42500000,0,0x43B08000,0x3CC08744)if c.seed==0 else tuple(PATTERNS[(c.seed+i)%len(PATTERNS)]^(c.seed<<i&0xFFFF)for i in range(7))
 for i,v in enumerate(values):put(m,s['D_800A5970']+i*4 if i<3 else s['D_800A597C']+(i-3)*4 if i<6 else s['D_800A5E58'],v)
 return m

def public(m):return{a:b for a,b in m.items()if not STACK-2048<=a<STACK+512}
def data(m,p,n):return bytes(m[p+i]for i in range(n))
def mock_effect(m,c,args,s):
 put(m,MARK,0x12345678);put(m,MARK+4,args[0]);put(m,MARK+8,args[4])
 if c.mode&1:
  for name,n in(('D_800A5970',12),('D_800A597C',12),('D_800A5E58',4)):
   for i in range(n):m[s[name]+i]^=0x5A
 if c.mode&2:
  for p in args[2:4]:
   for i in range(12):m[p+i]^=0xA5
 if c.mode&4:put(m,MARK+12,c.answer)

def call_reference(initial,c=Case(),s=None):
 s=symbols()if s is None else s;m=dict(initial);sp=STACK+c.phase-96;first,second=sp+84,sp+72
 for dst,src in((first,s['D_800A5970']),(second,s['D_800A597C'])):
  for i in range(3):put(m,dst+4*i,read(m,src+4*i))
 args=(c.owner,5,first,second,read(m,s['D_800A5E58']),2,300,255,255,255,255,1,0,0,255,1)
 observation=(args,data(m,first,12),data(m,second,12));mock_effect(m,c,args,s)
 return m,[(s['func_15160CDC'],args)],[observation]

def provider_reference(initial,args,c,entered):
 m=dict(initial);sp=entered-128;payload=sp+76;header=sp+116;zero=sp+64
 if not args[0]:return m,[],[],0
 put(m,payload,args[0]);m[payload+4]=m[args[0]+59];m[payload+5]=args[1]&255
 for dst,src in((payload+8,args[2]),(payload+20,args[3])):
  for i in range(3):put(m,dst+4*i,read(m,src+4*i))
 put(m,payload+32,args[4]);m[payload+36]=(1 if args[11]&255 else 0)|(2 if args[13]&255 else 0);m[payload+37]=args[12]&255
 m[header]=args[5]&255;m[header+1]=6;put(m,header+2,args[6]&65535,2);m[header+4]=17
 for i in range(3):put(m,zero+i*4,0)
 alloc_args=(header,zero,args[7],args[8],args[9],args[10],255,0,40,args[14]&255,args[15]);observations=[(alloc_args,data(m,header,5),data(m,zero,12),data(m,payload,40))];calls=[(FACTORY,alloc_args)]
 if c.mode&1:m[OWNER+59]^=0x5A
 put(m,MARK,0x87654321)
 answer=(OWNER if c.alias_output else OUTPUT)if c.allocated else 0
 if answer:
  calls.append((COPY,(answer+24,payload,40)));snapshot=data(m,payload,40)
  for i,b in enumerate(snapshot):m[answer+24+i]=b
 return m,calls,observations,answer

class EffectOracle(TimingOracle):
 def __init__(self,words,memory,c=Case(),entry=None,connected=None,s=None,arguments=None):
  self.effect_symbols=symbols()if s is None else s;self.case=c;self.effect=self.effect_symbols['func_15160CDC'];self.target=source.ENTRY if entry in(source.PARENT,source.EFFECT)else(source.ENTRY if entry is None else entry)
  super().__init__(words,memory,phase=c.phase,entry=source.ENTRY if entry is None else entry,arguments=(c.owner,)if arguments is None else arguments,connected=connected)
  self.trace=[];self.effect_observations=[];self.factory_observations=[];self.all_accesses=0;self.cut=None
 def access(self):
  if self.own_instruction:
   if self.all_accesses==self.cut:raise faults.AccessBoundary
   self.all_accesses+=1
 def get(self,address,size):
  v=super().get(address,size)
  if self.own_instruction:self.trace.append(('R',address,size,v))
  return v
 def put(self,address,value,size):
  super().put(address,value,size)
  if self.recording and self.own_instruction:self.trace.append(('W',address,size,value&((1<<(8*size))-1)))
 def record_call(self,target):
  n=16 if target==self.effect else 11 if target==FACTORY else 3 if target==COPY else 1 if target==source.ENTRY else None
  assert n is not None,('Unbounded effect provider',hex(target));args=self.arguments(n);self.calls.append((target,args));self.events.append(('CALL',target,args))
  if target==self.effect:self.effect_observations.append((args,data(self.memory,args[2],12),data(self.memory,args[3],12)))
  if target==FACTORY:self.factory_observations.append((args,data(self.memory,args[0],5),data(self.memory,args[1],12),data(self.memory,self.r[29]+76,40)))
 def hook(self,target):
  c=self.case;args=self.calls[-1][1]
  if target==self.effect:mock_effect(self.memory,c,args,self.effect_symbols);answer=c.answer
  elif target==FACTORY:
   if c.mode&1:self.memory[OWNER+59]^=0x5A
   put(self.memory,MARK,0x87654321);answer=(OWNER if c.alias_output else OUTPUT)if c.allocated else 0
  else:
   assert target==COPY and args[2]==40;dst,src,n=args;copy=data(self.memory,src,n)
   for i,b in enumerate(copy):self.memory[dst+i]=b
   answer=dst
  for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=answer&0xFFFFFFFF
