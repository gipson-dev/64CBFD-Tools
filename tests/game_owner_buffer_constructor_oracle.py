"""Owner buffer construction: ordered reference, bounded services and original caller routes."""
from dataclasses import dataclass,replace
import struct
from tools.experiments import game_owner_buffer_constructor_match as source
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
PAYLOAD,OWNER,OUTPUT,ALT,MARK=0x22000,0x24000,0x28000,0x26000,0x2C000
PREP,ALLOC,COPY,ZERO,SELECT=0x15191B8C,0x15167A68,0x10022EC0,0x100226F0,0x151D8E20
u32=lambda x:x&0xFFFFFFFF
@dataclass(frozen=True)
class Case:
 payload:int=PAYLOAD
 owner:int=OWNER
 identity:int=0x87
 extra:int=0
 priority:int=0xABCD00FF
 context:int=1
 outcome:int=1
 mode:int=0
 phase:int=0
 seed:int=0
 selector:int=0x123400FE

def symbols():return dict(func_15191B8C=PREP,func_15167A68=ALLOC,memcpy=COPY,bzero=ZERO,func_151D8E20=SELECT)
def args(c):return tuple(map(u32,(c.payload,c.extra,c.priority,c.context)))
def data(m,p,n):return bytes(m[u32(p+i)]for i in range(n))
def fixture(c=Case()):
 m={STACK+i:(i*17+c.seed+0xA5)&255 for i in range(-2048,2048)}
 for p,n in ((PAYLOAD-64,256),(OWNER-64,512),(OUTPUT-64,0x1000),(ALT-64,512),(MARK,32)):
  m.update({p+i:(i*13+c.seed+0x59)&255 for i in range(n)})
 put(m,c.payload,c.owner);m[u32(c.owner+59)]=c.identity&255
 return m
def public(m):return{a:b for a,b in m.items()if not STACK-2048<=a<STACK+2048}
def effect(m,c,home,stage):
 if stage==PREP:
  if c.mode&1:m[u32(c.payload+8)]^=0x80;m[u32(c.owner+59)]^=0x55
  if c.mode&2:put(m,home+4,0xFFFFFF80);put(m,home+8,0xCAFE0081);put(m,home+12,0x87654321)
  if c.mode&4:put(m,home,ALT)
 elif stage==ALLOC:
  if c.mode&8:m[u32(c.payload+6)]^=0x20
 elif stage==SELECT:
  if c.mode&16:put(m,OUTPUT+28,0x80000000);m[OUTPUT+44]=0xAA

def reference(initial,c=Case(),s=None,home=None):
 s=s or symbols();m=dict(initial);home=STACK+c.phase if home is None else home;notice=home-12
 for i,v in enumerate(args(c)[1:],1):put(m,home+4*i,v)
 owner=read(m,c.payload);put(m,notice,owner);identity=m[u32(read(m,c.payload)+59)];put(m,home,c.payload);m[notice+4]=identity
 prep=data(m,notice,5);calls=[(s['func_15191B8C'],(notice,14))];effect(m,c,home,PREP)
 context=read(m,home+12);size=u32(read(m,home+4)+0x300);priority=m[home+11]
 calls.append((s['func_15167A68'],(32,context,size,1,priority,1)));effect(m,c,home,ALLOC)
 if not c.outcome:return m,calls,0,prep,None
 payload=read(m,home);copied=data(m,payload,12);calls.append((s['memcpy'],(OUTPUT+16,payload,12)))
 for i in range(12):m[OUTPUT+16+i]=m[u32(payload+i)]
 for off,value in ((36,OUTPUT+48),(40,OUTPUT+768),(32,0),(28,0)):put(m,OUTPUT+off,value)
 calls.append((s['bzero'],(OUTPUT+48,720)))
 for i in range(720):m[OUTPUT+48+i]=0
 calls.append((s['func_151D8E20'],()));effect(m,c,home,SELECT);m[OUTPUT+44]=c.selector&255
 return m,calls,OUTPUT,prep,copied

class BufferOracle(FactoryOracle):
 def __init__(self,words,memory,c=Case(),entry=None,s=None,connected=None,arguments=None):
  super().__init__(words,memory,c,entry=source.ENTRY if entry is None else entry,s=s or symbols(),connected=connected,arguments=args(c)if arguments is None else arguments)
  self.notices=[];self.copies=[]
 def record_call(self,t):
  counts={source.ENTRY:4,self.syms['func_15191B8C']:2,self.syms['func_15167A68']:6,self.syms['memcpy']:3,self.syms['bzero']:2,self.syms['func_151D8E20']:0}
  assert t in counts,hex(t);a=tuple(map(u32,self.arguments(counts[t])));self.calls.append((t,a));self.events.append(('CALL',t,a))
  if t==source.ENTRY:self.target_home=self.r[29];self.case=replace(self.case,payload=a[0],extra=a[1],priority=a[2],context=a[3],owner=read(self.memory,a[0]))
  if t==self.syms['func_15191B8C']:self.notices.append(data(self.memory,a[0],5))
  if t==self.syms['memcpy']:self.copies.append(data(self.memory,a[1],a[2]))
 def hook(self,t):
  s=self.syms;c=self.case;a=self.calls[-1][1];value=0x76543210
  if t==s['func_15191B8C']:effect(self.memory,c,self.target_home,PREP)
  elif t==s['func_15167A68']:effect(self.memory,c,self.target_home,ALLOC);value=OUTPUT if c.outcome else 0
  elif t==s['memcpy']:
   assert 0<=a[2]<=16
   for i in range(a[2]):self.put(u32(a[0]+i),self.get(u32(a[1]+i),1),1)
   value=a[0]
  elif t==s['bzero']:
   assert 0<=a[1]<=768
   for i in range(a[1]):self.put(a[0]+i,0,1)
  elif t==s['func_151D8E20']:effect(self.memory,c,self.target_home,SELECT);value=c.selector
  else:raise AssertionError(hex(t))
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(value)

def state(m):return(m.r,m.f,m.hi,m.lo,m.condition,m.memory,m.events,m.calls,m.visits,m.trace,m.notices,m.copies)
