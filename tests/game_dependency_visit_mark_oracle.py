"""Ordered live-index reference and bounded visitor / recursive dispatcher execution."""
from dataclasses import dataclass
from tools.experiments import game_dependency_visit_mark_match as source
from tools.tests.test_game_effect_owner_ray import RayOracle
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests import test_game_actor_burst_consumer_match as faults
LIST,BITS,OTHER,CALLBACK=0x200000,0x90000,0xA0000,0x17000000
WRAPPER=0x1509CC94
@dataclass(frozen=True)
class Case:
 values:tuple=(2,7,8)
 seed:int=0
 mode:int=0
 phase:int=0
 alias:int=0
 callback:int=CALLBACK

def fixture(c=Case(),state=source.STATE,bitmap=source.BITMAP):
 m={STACK+i:(i*17+c.seed)&255 for i in range(-4096,256)};pointer=LIST if c.alias!=1 else state+2
 if c.alias==1:assert c.values==(2,7,8)
 for base in(LIST,pointer):m.update({base+i:(i*13+c.seed)&255 for i in range(-8,32)})
 indices={0,1,2,3,7,8,65535,*c.values,*((x+1)%65535 for x in c.values)}
 for index in indices:
  for d in(-1,0,1):m[state+index+d]=(index+d+c.seed)&255
 # Include the entire active byte ranges as modest sparse guest storage.
 for index in indices|{770,771,775,776}:
  for base in(BITS,OTHER):
   for d in(-1,0,1):m[base+(index>>3)+d]=(c.seed+d)&255
 if c.alias in(2,3):
  base=pointer-(c.values[0]>>3)if c.alias==2 and c.values else state
  for index in indices|{770,771,775,776}:m[base+(index>>3)]=c.seed&255
 if c.alias:
  for i in range(65536):m.setdefault(state+i,(i+c.seed)&255)
  for base in(BITS,OTHER):
   for i in range(8192):m.setdefault(base+i,c.seed&255)
  if c.alias==2 and c.values:
   for i in range(8192):m.setdefault(pointer-(c.values[0]>>3)+i,c.seed&255)
 # A state/list alias can rewrite the first terminator. Supply a second
 # sentinel so that this adversarial valid list still has a finite end.
 for i,x in enumerate((*c.values,65535,65535)):put(m,pointer+i*2,x,2)
 put(m,bitmap,(pointer-(c.values[0]>>3)if c.alias==2 and c.values else state if c.alias==3 else BITS))
 return m,pointer

def public(m):return{a:b for a,b in m.items()if not STACK-4096<=a<STACK+256}

def callback_effect(m,c,pointer,index,bitmap=source.BITMAP):
 if c.mode&1:put(m,pointer,(index+1)%65535,2)
 if c.mode&2:put(m,bitmap,OTHER)
 if c.mode&4:put(m,pointer+2,65535,2)
 if c.mode&8:put(m,pointer,65535,2)

def reference(initial,pointer,c=Case(),state=source.STATE,bitmap=source.BITMAP,callback=None):
 m=dict(initial);calls=[];index=read(m,pointer,2)
 while index!=65535:
  calls.append((c.callback if callback is None else callback,(index,)));callback_effect(m,c,pointer,index,bitmap)
  index=read(m,pointer,2);m[state+index]=3
  index=read(m,pointer,2);pointer+=2;at=read(m,bitmap)+(index>>3);m[at]=m[at]|(1<<(index&7));index=read(m,pointer,2)
 return m,calls

class VisitOracle(RayOracle):
 def __init__(self,words,memory,c=Case(),entry=source.ENTRY,connected=None,arguments=None,pointer=LIST,bitmap=source.BITMAP):
  TimingOracle.__init__(self,words,memory,phase=c.phase,entry=entry,arguments=arguments or(pointer,c.callback),connected=connected)
  self.case=c;self.trace=[];self.pointer=pointer;self.bitmap=bitmap;self.cut=None;self.access_count=0
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
  assert target in(self.case.callback,source.PARENT,source.ENTRY),('Unbounded callback',hex(target))
  args=self.arguments(2 if target==source.ENTRY else 1);self.calls.append((target,args));self.events.append(('CALL',target,args))
 def hook(self,target):
  assert target==self.case.callback
  callback_effect(self.memory,self.case,self.pointer,self.r[4],self.bitmap);self.pointer+=2
  for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=0x76543210

def graph_fixture(graph,seed=0,phase=0):
 c=Case(values=(),seed=seed,phase=phase);m,_=fixture(c)
 ids=set(graph)|{x for values in graph.values()for x in values}
 for node in ids:
  put(m,source.TABLE+node*20,LIST+node*32)
  for i,v in enumerate((*graph[node],65535)):put(m,LIST+node*32+i*2,v,2)
  m[source.STATE+node]=seed&255;m[BITS+(node>>3)]=seed&255
 return m,c

def graph_reference(initial,root):
 m=dict(initial);calls=[]
 def parent(node):
  pointer=read(m,source.TABLE+node*20);calls.append((source.ENTRY,(pointer,source.PARENT)));index=read(m,pointer,2)
  while index!=65535:
   calls.append((source.PARENT,(index,)));parent(index);index=read(m,pointer,2);m[source.STATE+index]=3;index=read(m,pointer,2);at=read(m,source.BITMAP)+(index>>3);m[at]|=1<<(index&7);pointer+=2;index=read(m,pointer,2)
 parent(root);return m,calls
