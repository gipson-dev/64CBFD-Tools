from pathlib import Path
import sys,struct,itertools
from dataclasses import dataclass
from tools.experiments import game_queue_append_1518abd0_match as packet
root=packet.ROOT;out=packet.OUT
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
ENTRY=0x1518abd0;BUILD=0x1518ab60;FREE=0x1516972c;TABLE=0x8008d5c0;CB=0x17000000;Q=0x30000;HEAD=0x31000;TAIL=0x32000;NEW=0x33000;OWNER=0x34000;MARK=0x35000
S=dict(D_8008D5C0=TABLE,func_1516972C=FREE,func_1518AB60=BUILD)
u32=lambda x:x&0xffffffff
signed=lambda x:((x&0xffffffff)^0x80000000)-0x80000000
@dataclass(frozen=True)
class Case:
 phase:int=0;present:int=1;allocation:int=1;selector:int=1;count:int=1;limit:int=1;nonempty:int=1;evictSelector:int=1

def fixture(c):
 m={STACK+c.phase+i:(i*17+0xa5)&255 for i in range(-2048,1024)}
 for base,n in ((Q,0x80),(HEAD,0x80),(TAIL,0x80),(NEW,0x80),(OWNER,0x80),(MARK,0x20),(TABLE,1024)):
  m.update({base+i:0 for i in range(n)})
 for i in range(256):put(m,TABLE+i*4,CB+i*4)
 put(m,Q+0x10,TAIL if c.nonempty else 0);put(m,Q+0x14,HEAD if c.nonempty else 0);put(m,Q+0x18,c.limit);put(m,Q+0x1c,c.count);put(m,Q+0x20,0x8a9b,2);put(m,Q+0x22,0xbeef,2)
 put(m,HEAD+0x10,OWNER+8);put(m,HEAD+0x18,TAIL if c.nonempty else 0);m[HEAD+0x1c]=c.evictSelector
 put(m,TAIL+0x10,OWNER+12);put(m,TAIL+0x18,0);m[TAIL+0x1c]=2
 return m

def reference(c):
 m=fixture(c);calls=[];q=Q if c.present else 0;sel=c.selector&255
 def callback(s,arg):calls.append((CB+4*s,(arg,)));put(m,MARK,arg)
 if q==0:
  if sel:callback(sel,OWNER)
  return m,calls,0
 calls.append((BUILD,(OWNER,sel)))
 if not c.allocation:
  if sel:callback(sel,OWNER)
  return m,calls,0
 put(m,NEW+0x10,OWNER);put(m,NEW+0x14,0);put(m,NEW+0x18,0);m[NEW+0x1c]=sel
 tail=read(m,q+0x10);put(m,NEW+0x14,tail)
 if tail:put(m,tail+0x18,NEW)
 else:put(m,q+0x14,NEW)
 put(m,q+0x10,NEW);put(m,NEW+0x18,0)
 count=u32(read(m,q+0x1c)+1);limit=signed(read(m,q+0x18));duration=read(m,q+0x20,2);put(m,q+0x1c,count);put(m,q+0x22,duration,2)
 if limit<signed(count):
  old=read(m,q+0x14);put(m,q+0x1c,u32(count-1));next=read(m,old+0x18)
  if next:put(m,next+0x14,0);put(m,q+0x14,read(m,old+0x18))
  else:put(m,q+0x10,0);put(m,q+0x14,0)
  selector=m[old+0x1c]
  if selector:callback(selector,read(m,old+0x10))
  calls.append((FREE,(old,)));put(m,MARK+4,old)
 return m,calls,1
class Machine(FactoryOracle):
 def __init__(self,w,c):
  self.c=c;super().__init__(w,fixture(c),c,entry=ENTRY,s=S,arguments=(Q if c.present else 0,OWNER,c.selector))
 def record_call(self,t):
  if t==BUILD:a=tuple(self.arguments(2))
  elif t==FREE or CB<=t<CB+1024:a=tuple(self.arguments(1))
  else:raise AssertionError(('unexpected call',hex(t)))
  self.calls.append((t,a))
 def hook(self,t):
  a=self.calls[-1][1];answer=0xabcdefff
  if t==BUILD:
   if self.c.allocation:
    answer=NEW;put(self.memory,NEW+0x10,a[0]);put(self.memory,NEW+0x14,0);put(self.memory,NEW+0x18,0);self.memory[NEW+0x1c]=a[1]&255
   else:answer=0
  elif t==FREE:put(self.memory,MARK+4,a[0])
  else:put(self.memory,MARK,a[0])
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=answer

def public(m,c):return {a:b for a,b in m.items() if not STACK+c.phase-2048<=a<STACK+c.phase+1024}
def program(path):raw,refs=payload(path,'func_1518ABD0');return bound_blob(raw,refs,S)
