"""Descriptor geometry command with opaque, explicitly bounded effect providers."""
from dataclasses import dataclass
import itertools,struct
from tools.experiments import game_actor_descriptor_effect_match as source
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_effect_position_payload import complete
ACTOR,DESCRIPTOR,MATRICES,ALTERNATE=0x20000,0x30000,0x40000,0x50000
VALUES=(0,0x80000000,0x3f800000,0xbf800000,0x7f800000,0x7fc12345,1,0x7f7fffff)
@dataclass(frozen=True)
class Case:
 found:bool=True
 geometry:bool=True
 selector:int=0
 parameter:int=1
 index:int=0
 mode:int=0
 phase:int=0
 pattern:int=0

def fixture(c=Case()):
 m={STACK+i:(i*17+0xa5)&255 for i in range(-2048,1024)}
 for address,n in ((ACTOR,0x340),(DESCRIPTOR,128)):
  m.update({address+i:(i*13+c.pattern)&255 for i in range(-32,n)})
 put(m,ACTOR+0x1d4,MATRICES);m[DESCRIPTOR+2]=c.index
 return m

def addresses(c):
 home=STACK+c.phase
 return home-72,home-84,home-96,home-108,home-120

def public(m):return{a:b for a,b in m.items()if not STACK-2048<=a<STACK+1024}
def words(m,p,n):return tuple(read(m,p+i*4)for i in range(n))

def lookup_effect(m,c):
 if c.mode&1:put(m,ACTOR+0x1d4,ALTERNATE)

def geometry_effect(m,c,args):
 # The six-vector array is 72 bytes; the four remaining outputs are 12 bytes each.
 for j,(address,count)in enumerate(zip(args[:5],(18,3,3,3,3))):
  for i in range(count):put(m,address+4*i,VALUES[(i+j+c.pattern)%len(VALUES)])
 if c.mode&2:m[DESCRIPTOR+2]=(c.index+1)&255

def primary_effect(m,c,p):
 if c.mode&4:
  put(m,p,0xc1200000);m[DESCRIPTOR+2]=(c.index+2)&255;put(m,ACTOR+0x1d4,ALTERNATE)

def secondary_effect(m,c,origin,points):
 if c.mode&8:put(m,origin+4,0x41200000);put(m,points+68,0x44340000)

def reference(initial,c=Case(),targets=None):
 t=(source.LOOKUP,source.GEOMETRY,source.PRIMARY,source.SECONDARY,source.FINAL)if targets is None else targets
 m=dict(initial);calls=[];packets=[];points,origin,direction,velocity,other=addresses(c);selector=c.selector&255;parameter=c.parameter&0xffffffff
 calls.append((t[0],(ACTOR,)));lookup_effect(m,c)
 if not c.found:return m,calls,packets
 args=(points,origin,direction,velocity,other,ACTOR,DESCRIPTOR);calls.append((t[1],args));geometry_effect(m,c,args)
 if not c.geometry:return m,calls,packets
 calls.append((t[2],(origin,selector,parameter)));packets.append((t[2],words(m,origin,3)));primary_effect(m,c,origin)
 matrix=(read(m,ACTOR+0x1d4)+m[DESCRIPTOR+2]*64)&0xffffffff
 calls.append((t[3],(direction,velocity,matrix,ACTOR,0x3f800000,selector,parameter)));packets.append((t[3],words(m,direction,3),words(m,velocity,3)));secondary_effect(m,c,origin,points)
 calls.append((t[4],(origin,points,selector,parameter)));packets.append((t[4],words(m,origin,3),words(m,points,18)))
 return m,calls,packets

class DescriptorOracle(TimingOracle):
 def __init__(self,body,memory,c=Case(),entry=source.ENTRY,targets=None,connected=None):
  super().__init__(body,memory,phase=c.phase,entry=entry,arguments=(ACTOR,c.selector,c.parameter),connected=connected)
  self.case=c;self.targets=(source.LOOKUP,source.GEOMETRY,source.PRIMARY,source.SECONDARY,source.FINAL)if targets is None else targets;self.trace=[];self.packets=[]
 def get(self,a,n):
  v=super().get(a,n)
  if self.own_instruction:self.trace.append(('R',a,n,v))
  return v
 def put(self,a,v,n):
  super().put(a,v,n)
  if self.recording and self.own_instruction:self.trace.append(('W',a,n,v&((1<<(8*n))-1)))
 def record_call(self,target):
  assert target in self.targets,hex(target);count=(1,7,3,7,4)[self.targets.index(target)];args=tuple(self.arguments(count));self.calls.append((target,args));self.events.append(('CALL',target,args))
  if target==self.targets[2]:self.packets.append((target,words(self.memory,args[0],3)))
  if target==self.targets[3]:self.packets.append((target,words(self.memory,args[0],3),words(self.memory,args[1],3)))
  if target==self.targets[4]:self.packets.append((target,words(self.memory,args[0],3),words(self.memory,args[1],18)))
 def hook(self,target):
  c=self.case;args=self.calls[-1][1];points,origin,_,_,_=addresses(c);value=0x76543210
  if target==self.targets[0]:lookup_effect(self.memory,c);value=DESCRIPTOR if c.found else 0
  elif target==self.targets[1]:geometry_effect(self.memory,c,args);value=1 if c.geometry else 0
  elif target==self.targets[2]:primary_effect(self.memory,c,args[0])
  elif target==self.targets[3]:secondary_effect(self.memory,c,origin,points)
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.r[2]=value;self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011

def corpus():
 for found,geometry,selector,index,mode,phase in itertools.product((False,True),(False,True),(0,37,255),(0,255),range(16),(0,8)):
  yield Case(found,geometry,selector,0x80000000|selector,index,mode,phase,pattern=mode%8)
 for value in range(256):
  yield Case(selector=0xab000000|value,index=value,parameter=value,mode=value&15,pattern=value%8)

ENTRY,CASE,END,TABLE=0x15028810,0x15028920,0x15029BA4,0x80096CEC
PROVIDER,HEAD,OTHER=0x1503195C,0x800C3EE0,0x32000
from tools.tests import test_game_actor_burst_consumer_match as faults
class WindowBoundary(Exception):pass
class WindowCode(faults.TrackedCode):
 def __getitem__(self,pc):
  if pc==END:raise WindowBoundary
  return super().__getitem__(pc)
class Caller(DescriptorOracle):
 def __init__(self,words,memory,c,prefix,case_words):
  connected=dict(zip(range(source.ENTRY,source.ENTRY+196,4),words));connected.update(zip(range(CASE,CASE+20,4),case_words));super().__init__(prefix,memory,c,entry=ENTRY,connected=connected);self.code=WindowCode(self.code,self);self.children=[]
 def record_call(self,target):
  if target==source.ENTRY:
   args=tuple(self.arguments(3));self.children.append(args);self.calls.append((target,args));self.events.append(('CALL',target,args))
  else:super().record_call(target)

class Lookup(DescriptorOracle):
 def __init__(self,words,memory,c,connected):super().__init__(words,memory,c,connected=connected)
 def record_call(self,target):
  if target==PROVIDER:
   args=tuple(self.arguments(3));self.calls.append((target,args));self.events.append(('CALL',target,args))
  else:super().record_call(target)
 def hook(self,target):
  assert target not in(source.LOOKUP,PROVIDER);super().hook(target)
