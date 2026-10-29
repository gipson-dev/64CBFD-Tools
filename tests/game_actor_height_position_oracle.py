"""Ordered actor/output aliases, vertical interval packets and bounded providers."""
from dataclasses import dataclass
import itertools,struct
from tools.experiments import game_actor_height_position_match as source
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_actor_direction_point_oracle import DirectionOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.test_game_point_transform_match import put,read
ACTOR,POSITION,RESULT=0x20000,0x30000,0x34000
VALUES=(0,0x80000000,0x3f800000,0xbf800000,0x42c80000,0xc2c80000,0x7f800000,0xff800000,0x7fc12345,1,0x7f7fffff,0xff7fffff)
@dataclass(frozen=True)
class Case:
 pattern:int=0
 query:bool=True
 position_layout:int=0
 result_layout:int=0
 mode:int=0
 returned:int=1
 fourth:int=0
 phase:int=0
 position_override:int|None=None
 result_override:int|None=None
 child_home:int|None=None

def position(c):return c.position_override if c.position_override is not None else(POSITION,ACTOR+0x14,ACTOR+0x18,ACTOR+0x180,ACTOR+0x17c,ACTOR+0x1c)[c.position_layout]
def result(c):return 0 if not c.query else c.result_override if c.result_override is not None else(RESULT,position(c),ACTOR+0x14,ACTOR+0x17c)[c.result_layout]
def fixture(c=Case(),threshold=source.THRESHOLD):
 m={STACK+i:(i*17+0xa5)&255 for i in range(-2048,2048)}
 for base,n in((ACTOR,0x340),(POSITION,128),(RESULT,128)):
  m.update({base+i:(i*13+c.pattern)&255 for i in range(-32,n)})
 for offset,value in((0x14,VALUES[c.pattern%12]),(0x18,VALUES[(c.pattern+3)%12]),(0x1c,VALUES[(c.pattern+6)%12]),(0x180,VALUES[(c.pattern+9)%12])):put(m,ACTOR+offset,value)
 put(m,threshold,VALUES[(c.pattern+4)%12]);return m

def public(m):return{a:b for a,b in m.items()if not STACK-2048<=a<STACK+2048}
def initializer_effect(m,c,d,p):
 for i in range(36):m[d+i]=(i*7+c.mode)&255
 put(m,d,0x43960000)
 if c.mode&1:put(m,p+4,0x442f0000)
def query_effect(m,c,d,p):
 m[d+28]=0xd7
 if c.mode&2:put(m,p,0xc3480000)

def reference(initial,c=Case(),threshold=source.THRESHOLD,initialize=source.INITIALIZE,query=source.QUERY):
 m=dict(initial);p,d=position(c),result(c);calls=[];packets=[]
 put(m,p,read(m,ACTOR+0x14));height=read(m,ACTOR+0x180)
 put(m,p+4,height if floating(read(m,threshold))<floating(height)else read(m,ACTOR+0x18));put(m,p+8,read(m,ACTOR+0x1c))
 if not d:return m,calls,packets,1
 start=(STACK+c.phase if c.child_home is None else c.child_home)-12;put(m,start,read(m,p));put(m,start+4,bits(floating(read(m,p+4))+100.0));put(m,start+8,read(m,p+8))
 calls.append((initialize,(d,ACTOR)));initializer_effect(m,c,d,p)
 lower=bits(floating(read(m,p+4))-100.0);calls.append((query,(start,0,lower,d)));packets.append(tuple(read(m,start+4*i)for i in range(3)));query_effect(m,c,d,p)
 return m,calls,packets,c.returned&0xffffffff

class HeightOracle(TimingOracle):
 def __init__(self,words,memory,c=Case(),entry=source.ENTRY,threshold=source.THRESHOLD,initialize=source.INITIALIZE,query=source.QUERY,connected=None,arguments=None):
  super().__init__(words,memory,phase=c.phase,entry=entry,arguments=(position(c),ACTOR,result(c),c.fourth)if arguments is None else arguments,connected=connected)
  self.case,self.threshold,self.initialize,self.query=c,threshold,initialize,query;self.trace=[];self.packets=[]
 def get(self,a,n):
  v=super().get(a,n)
  if self.own_instruction:self.trace.append(('R',a,n,v))
  return v
 def put(self,a,v,n):
  super().put(a,v,n)
  if self.recording and self.own_instruction:self.trace.append(('W',a,n,v&((1<<(n*8))-1)))
 def execute(self,word):
  if word>>26 in(34,38,42,46):return DirectionOracle.execute(self,word)
  return super().execute(word)
 def record_call(self,target):
  assert target in(self.initialize,self.query),hex(target);args=tuple(self.arguments(2 if target==self.initialize else 4));self.calls.append((target,args));self.events.append(('CALL',target,args))
  if target==self.query:self.packets.append(tuple(read(self.memory,args[0]+4*i)for i in range(3)))
 def hook(self,target):
  c=self.case;args=self.calls[-1][1];p=position(c)
  if target==self.initialize:initializer_effect(self.memory,c,args[0],p);value=0x76543210
  else:query_effect(self.memory,c,args[3],p);value=c.returned&0xffffffff
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.r[2]=value;self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011

def corpus():
 for pattern,query,layout,mode,phase in itertools.product(range(12),(False,True),range(6),range(4),(0,8)):
  yield Case(pattern,query,layout,mode=mode,returned=(0,1,0xffffffff,0x80000000)[mode],phase=phase)
 for pattern,layout,result_layout,mode in itertools.product((0,3,9),range(6),range(4),range(4)):
  yield Case(pattern,position_layout=layout,result_layout=result_layout,mode=mode)
 for fourth in range(256):yield Case(pattern=fourth%12,fourth=0xab000000|fourth,mode=fourth&3)

PARENT,END,SKIP=0x150BAA14,0x150BAA64,0x150BABD0
CHECK,CLASSIFY,FALLBACK,ENTITIES=0x15145C90,0x15047004,0x1504697C,0x800DBEF4
from tools.tests import test_game_actor_burst_consumer_match as faults
class WindowBoundary(Exception):pass
class WindowCode(faults.TrackedCode):
 def __getitem__(self,pc):
  if pc in(END,SKIP):raise WindowBoundary
  return super().__getitem__(pc)
class Caller(HeightOracle):
 def __init__(self,words,memory,c,parent_words):
  super().__init__(parent_words,memory,c,entry=PARENT,connected=dict(zip(range(source.ENTRY,source.ENTRY+208,4),words)),arguments=(ACTOR,c.fourth,0x12345678));self.code=WindowCode(self.code,self);self.children=[]
 def record_call(self,target):
  if target==source.ENTRY:
   args=tuple(self.arguments(4));self.calls.append((target,args));self.events.append(('CALL',target,args));self.children.append(args)
  else:super().record_call(target)

class Helpers(HeightOracle):
 def __init__(self,body,memory,c,index,answer,status,mutation,connected):
  super().__init__(body,memory,c,connected=connected);self.index,self.answer,self.status,self.mutation=index,answer,status,mutation
 def record_call(self,target):
  if target in(CHECK,CLASSIFY,FALLBACK):
   args=tuple(self.arguments({CHECK:1,CLASSIFY:3,FALLBACK:4}[target]));self.calls.append((target,args));self.events.append(('CALL',target,args))
  else:super().record_call(target)
 def hook(self,target):
  assert target not in(source.INITIALIZE,source.QUERY);d=result(self.case)
  if target==CHECK:
   assert self.calls[-1][1]==(self.index-1,)
   if self.mutation:self.memory[d+28]=0xa0;put(self.memory,ACTOR+0x1a0,0,2);put(self.memory,ENTITIES,0)
   value=self.answer
  elif target==CLASSIFY:self.memory[d+28]^=0x10;value=self.status
  else:self.memory[d+28]^=0x20;value=self.case.returned
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.r[2]=value&0xffffffff;self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011
def expected(initial,c,flag,index,answer,status,mutation):
 m=dict(initial);p,d=position(c),result(c);home=STACK+c.phase;start=home-12;calls=[]
 put(m,p,read(m,ACTOR+0x14));put(m,p+4,read(m,ACTOR+0x180));put(m,p+8,read(m,ACTOR+0x1c))
 ray=(read(m,p),bits(floating(read(m,p+4))+100.0),read(m,p+8))
 for i,v in enumerate(ray):put(m,start+4*i,v)
 calls.append((source.INITIALIZE,(d,ACTOR)));put(m,d,read(m,ACTOR+0x180))
 if flag:
  for i,v in enumerate((988,19,1034,-1012,19,34,988,19,-966)):put(m,d+4+2*i,v&65535,2)
 else:
  for i in range(18):m[d+4+i]=m[ACTOR+0x18c+i]
 put(m,d+24,read(m,ACTOR+0x184));m[d+28]=6;m[d+29]=2 if index else 1;put(m,d+32,0x38000+(index-1)*160 if index else 0)
 if index:
  calls.append((CHECK,(index-1,)))
  if mutation:m[d+28]=0xa0;put(m,ACTOR+0x1a0,0,2);put(m,ENTITIES,0)
 m[d+28]|=int(not index or bool(answer));lower=bits(floating(read(m,p+4))-100.0)
 calls.append((source.QUERY,(start,0,lower,d)));calls.append((CLASSIFY,(start,lower,d)));m[d+28]^=0x10
 if status==0:calls.append((FALLBACK,(start,0,lower,d)));m[d+28]^=0x20;value=c.returned&0xffffffff
 else:value=0 if status==1 else 1
 return m,calls,[ray],value
