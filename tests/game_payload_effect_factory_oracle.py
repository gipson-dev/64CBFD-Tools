"""Seven-argument payload factory and bounded original allocation chain."""
from dataclasses import dataclass,replace
import struct
from tools.experiments import game_payload_effect_factory_match as source
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
OWNER,OUTPUT,BODY,STATE,MARK=0x30000,0x50000,0x60000,0x70000,0x80000
FACTORY,WRAPPER,SPAWN,ALLOCATE,FREE,COPY=0x151602C0,0x1516037C,0x1515D5F8,0x15167A68,0x1515F10C,0x10022EC0
WINDOW,WINDOW_WORDS,END=0x150EF33C,9,0x150EF360
HELPERS=((FACTORY,0x18D770,47),(WRAPPER,0x18D82C,32))
u32=lambda n:n&0xFFFFFFFF
@dataclass(frozen=True)
class Case:
 a:int=0x12340046
 b:int=0x567800FF
 c:int=0x87650082
 d:int=0xFEDC0000
 owner:int=OWNER
 fifth:int=0x123400FF
 sixth:int=1
 outcome:int=2
 mutation:int=0
 phase:int=0
 seed:int=0
def symbols():return dict(func_151602C0=FACTORY,memcpy=COPY)
def args(c):return tuple(map(u32,(c.a,c.b,c.c,c.d,c.owner,c.fifth,c.sixth)))
def fixture(c=Case()):
 m={STACK+i:(i*17+c.seed*13+0xA5)&255 for i in range(-2048,512)}
 for base,n in((OWNER,128),(OUTPUT-32,128),(BODY,128),(STATE,128),(MARK,32)):m.update({base+i:(i*29+c.seed*11+0x5A)&255 for i in range(n)})
 return m
def data(m,p,n):return bytes(m[p+i]for i in range(n))
def public(m):return{a:b for a,b in m.items()if not STACK-2048<=a<STACK+512}
def effect(m,c,header,position):
 put(m,MARK,0x13579BDF)
 if c.mutation&1:m[header+4]^=0x55;put(m,position,0x87654321)
 if c.mutation&2:
  # Only the guest experiment exposes incoming homes; native tests do not.
  put(m,header+12,0xABCDEF01);put(m,header+28,0xDEADBEEF)
def reference(initial,c=Case(),s=None,connected=False,home=None):
 s=symbols()if s is None else s;m=dict(initial);home=STACK+c.phase if home is None else home;sp=home-88;header,position,payload=sp+76,sp+64,sp+60
 put(m,payload,c.owner);m[header]=2;m[header+1]=255;put(m,header+2,300,2);m[header+4]=33
 for i in range(3):put(m,position+4*i,0)
 a=(header,position,c.a&255,c.b&255,c.c&255,c.d&255,255,0,4,c.fifth&255,u32(c.sixth));calls=[(s['func_151602C0'],a)];observations=[(data(m,header,6),data(m,position,12),a)]
 if connected:
  bodyargs=(0,0,0,*a[2:8],0);calls.append((SPAWN,bodyargs));effect(m,c,header,position)
  if c.outcome:
   calls.append((WRAPPER,(header,BODY,4,c.fifth&255,u32(c.sixth))));calls.append((ALLOCATE,(53,u32(c.sixth),28,1,c.fifth&255,1)))
   if c.outcome==1:put(m,MARK+4,BODY);calls.append((FREE,(BODY,)))
 else:effect(m,c,header,position)
 answer=OUTPUT if c.outcome==2 else 0
 if answer:
  if connected:calls.append((s['memcpy'],(answer+14,header,6)))
  for i,b in enumerate(data(m,header,6)):m[answer+14+i]=b
  put(m,answer+20,BODY);m[answer+14]|=2
  calls.append((s['memcpy'],(answer+24,payload,4)))
  for i,b in enumerate(data(m,payload,4)):m[answer+24+i]=b
 return m,calls,answer,observations
class FactoryOracle(TimingOracle):
 def __init__(self,words,memory,c=Case(),entry=None,s=None,connected=None,arguments=None):
  self.case=c;self.syms=symbols()if s is None else s;self.factory_header=self.factory_position=None
  super().__init__(words,memory,phase=c.phase,entry=source.ENTRY if entry is None else entry,arguments=args(c)if arguments is None else arguments,connected=connected)
  self.trace=[];self.all_accesses=0;self.cut=None;self.factory_observations=[]
 def execute(self,word):
  if word>>26!=0x20:return super().execute(word)
  # The signed-byte negative control uses LB; sign-extend exactly as MIPS.
  prior=self.own_instruction;self.own_instruction=True;self.dispatched_word=word
  try:
   offset=((word&65535)^32768)-32768;value=self.get(u32(self.r[word>>21&31]+offset),1);self.r[word>>16&31]=u32((value^128)-128);self.r[0]=0
  finally:self.own_instruction=prior
 def access(self):
  if self.own_instruction:
   if self.all_accesses==self.cut:raise faults.AccessBoundary
   self.all_accesses+=1
 def get(self,p,n):
  v=super().get(p,n)
  if self.own_instruction:self.trace.append(('R',p,n,v))
  return v
 def put(self,p,v,n):
  super().put(p,v,n)
  if self.recording and self.own_instruction:self.trace.append(('W',p,n,v&((1<<(8*n))-1)))
 def record_call(self,t):
  counts={source.ENTRY:7,self.syms['func_151602C0']:11,self.syms['memcpy']:3,SPAWN:10,WRAPPER:5,ALLOCATE:6,FREE:1};assert t in counts,hex(t)
  a=tuple(map(u32,self.arguments(counts[t])));self.calls.append((t,a));self.events.append(('CALL',t,a))
  if t==self.syms['func_151602C0']:
   self.factory_header,self.factory_position=a[:2];self.factory_observations.append((data(self.memory,a[0],6),data(self.memory,a[1],12),a))
 def hook(self,t):
  c=self.case;a=self.calls[-1][1];s=self.syms
  if t in(s['func_151602C0'],SPAWN):effect(self.memory,c,self.factory_header,self.factory_position)
  if t==s['func_151602C0']:
   value=OUTPUT if c.outcome==2 else 0
   if value:
    for i,b in enumerate(data(self.memory,a[0],6)):self.memory[value+14+i]=b
    put(self.memory,value+20,BODY);self.memory[value+14]|=2
  elif t==SPAWN:value=BODY if c.outcome else 0
  elif t==ALLOCATE:value=OUTPUT if c.outcome==2 else 0
  elif t==FREE:put(self.memory,MARK+4,a[0]);value=0xDEADBEEF
  else:
   assert t==s['memcpy']and 0<=a[2]<=64,(t,a);copy=data(self.memory,a[1],a[2])
   for i,b in enumerate(copy):self.memory[a[0]+i]=b
   value=a[0]
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(value)
def helper_code(rom):
 result={}
 for entry,offset,n in HELPERS:
  assert offset==entry-0x15000000+0x2D4B0;result.update(zip(range(entry,entry+n*4,4),struct.unpack_from('>%dI'%n,rom,offset)))
 return result
def caller_machine(rom,words,c=Case(),connected=True):
 c=replace(c,a=70,b=255,c=130,d=0,fifth=c.fifth&255);initial=fixture(c);home=STACK+c.phase;code=helper_code(rom)if connected else{};code.update(zip(range(source.ENTRY,source.ENTRY+4*len(words),4),words));code[END]=0
 body=struct.unpack_from('>9I',rom,WINDOW-0x15000000+0x2D4B0);m=FactoryOracle(body,initial,c,entry=WINDOW,connected=code)
 m.r[16]=STATE;m.r[19]=c.fifth;m.r[20]=u32(c.sixth);m.r[21]=u32(c.owner);m.before=m.r[:];m.code=WindowCode(m.code,m);m.code.ends=(END,)
 expected,calls,value,observations=reference(initial,c,connected=connected,home=home);put(expected,STATE+44,value)
 return m,(expected,[(source.ENTRY,args(c))]+calls,value,observations)
