"""Queued retirement: ordered aliases, opaque effects and original dispatch/helpers."""
from dataclasses import dataclass,replace
import itertools,struct
from tools.experiments import game_queued_entry_retire_match as source
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
QUEUE,ENTRY_NODE,NEXT,ARG,OTHER,ALT,MARK=0x30000,0x31000,0x32000,0x33000,0x34000,0x35000,0x36000
CB1,CB2,CBNEG,EFFECT=0x150BB408,0x150CBF5C,0x17000100,0x1513F6C0
FREE,SCAN,ADAPTER,UNLINK,CUSTOM=0x1516972C,0x151696DC,0x15169804,0x15168B10,0x17000200
COUNT,SLOTS,REGISTRY=0x800DD190,0x800DD198,0x8008B4A8
WINDOW,END=0x15167158,0x15167188
HELPERS=((CB1,18),(CB2,7),(FREE,28),(SCAN,20),(ADAPTER,8))
u32=lambda n:n&0xFFFFFFFF
half=lambda n:((n&65535)^32768)-32768
signed=lambda n:((n&0xFFFFFFFF)^0x80000000)-0x80000000
@dataclass(frozen=True)
class Case:
 count:int=3
 timer:int=-1
 ticks:int=1
 flags:int=1
 selector:int=1
 layout:int=0
 mode:int=0
 phase:int=0
 seed:int=0
 category:int=30
 cleanup:int=0
 scan_count:int=2

def symbols():return dict(D_8008D5C0=0x8008D5C0,D_800BE9E4=0x800BE9E4,func_1516972C=FREE)
def node(c):return QUEUE if c.layout==3 else ENTRY_NODE
def next_node(c):return (NEXT,ENTRY_NODE+4,QUEUE,0,ENTRY_NODE,0)[c.layout]
def public(m):return{a:b for a,b in m.items()if not STACK-2048<=a<STACK+1024}
def fixture(c=Case(),s=None):
 s=s or symbols();m={STACK+i:(i*17+c.seed+0xA5)&255 for i in range(-2048,1024)}
 for base in(QUEUE,ENTRY_NODE,NEXT,ARG,OTHER,ALT,MARK):
  for i in range(-16,256):m[base+i]=(i*29+c.seed+0x5A)&255
 for base in(QUEUE,OTHER):
  for off,value,size in((8,NEXT+128,4),(0x10,ALT,4),(0x14,node(c),4),(0x1C,c.count,4),(0x22,c.timer,2),(0x24,c.flags,1)):put(m,base+off,value,size)
 for base in(node(c),ALT):
  for off,value,size in((0,c.category,1),(8,NEXT+64,4),(0x10,ARG,4),(0x18,next_node(c),4),(0x1C,c.selector,1)):put(m,base+off,value,size)
 # Alias layout 3 intentionally overlays the selector with the count's high byte.
 put(m,s['D_800BE9E4'],c.ticks)
 for i in range(-256,256):put(m,u32(s['D_8008D5C0']+4*i),CBNEG if i<0 else CB2 if i==2 else CB1)
 put(m,COUNT,c.scan_count,1)
 for i in range(4):put(m,SLOTS+4*i,node(c)if i in(0,2)else ALT)
 put(m,REGISTRY+29*52,source.ENTRY);put(m,REGISTRY+40+c.category*52,CUSTOM if c.cleanup else 0)
 return m

def effect(m,c,queue,arg,release=False,home=None):
 home=STACK+c.phase if home is None else home
 if release:
  put(m,MARK+4,arg)
  if c.mode&4:put(m,queue+0x1C,0)
  if c.mode&8:put(m,home,OTHER)
 else:
  put(m,MARK,arg)
  if c.mode&1:put(m,queue+0x1C,7);put(m,queue+0x14,ALT)
  if c.mode&2:put(m,node(c)+0x10,OTHER);put(m,node(c)+0x18,ALT)
  if c.mode&16:put(m,home,OTHER)
  if c.mode&32:put(m,home-8,ALT)

def reference(initial,c=Case(),s=None,real=False,home=None):
 s=s or symbols();m=dict(initial);q=QUEUE;home=STACK+c.phase if home is None else home;calls=[]
 def call(t,*args):calls.append((t,tuple(map(u32,args))))
 if read(m,q+0x1C)==0:return m,calls
 timer=half(read(m,q+0x22,2))
 if timer>=0:
  if m[q+0x24]&1:put(m,q+0x22,u32(timer-read(m,s['D_800BE9E4']))&65535,2)
  return m,calls
 e=read(m,q+0x14);n=read(m,e+0x18)
 if n:put(m,n+0x14,0);put(m,q+0x14,read(m,e+0x18))
 else:put(m,q+0x10,0);put(m,q+0x14,0)
 selector=m[e+0x1C]
 if selector:
  target=read(m,u32(s['D_8008D5C0']+selector*4));arg=read(m,e+0x10);call(target,arg)
  if real:
   if target==CB1:
    flags=read(m,arg+0x18);put(m,arg+0x1C,50,2);put(m,arg+0x18,flags|1);put(m,arg+0xB2,5,2);put(m,arg+0xB0,50,2);call(EFFECT,arg,6,m[arg+0x81]);put(m,MARK,arg)
   else:assert target==CB2;flags=read(m,arg+0x58);put(m,arg+0x1C,32,2);put(m,arg+0x58,flags|1)
  else:
   effect(m,c,q,arg,home=home)
   if c.mode&16:q=OTHER
   if c.mode&32:e=ALT
 call(s['func_1516972C'],e)
 if real:
  call(SCAN,e)
  count=((m[COUNT]^128)-128)
  for i in range(max(count,0)):
   if read(m,SLOTS+4*i)==e:put(m,SLOTS+4*i,read(m,e+8))
  category=m[e]
  if category>=2:
   target=read(m,REGISTRY+40+category*52)
   if target:call(target,e)
   else:call(ADAPTER,e);call(UNLINK,e,1)
   effect(m,c,q,e,True,home)
 else:effect(m,c,q,e,True,home)
 if c.mode&8 and(not real or m[e]>=2):q=OTHER
 put(m,q+0x1C,u32(read(m,q+0x1C)-1));return m,calls

class RetireOracle(FactoryOracle):
 def __init__(self,words,memory,c=Case(),entry=None,s=None,connected=None,real=False):
  self.active_queue=QUEUE;self.real=real;super().__init__(words,memory,c,entry=source.ENTRY if entry is None else entry,s=s or symbols(),connected=connected,arguments=(QUEUE,))
 def execute(self,word):
  if word>>26==0 and word&63==3:self.r[word>>11&31]=u32(signed(self.r[word>>16&31])>>(word>>6&31));self.r[0]=0
  else:super().execute(word)
 def record_call(self,t):
  counts={source.ENTRY:1,CB1:1,CB2:1,CBNEG:1,self.syms['func_1516972C']:1,SCAN:1,ADAPTER:1,UNLINK:2,CUSTOM:1,EFFECT:3}
  assert t in counts,('Unbounded provider',hex(t));a=tuple(self.arguments(counts[t]));self.calls.append((t,a));self.events.append(('CALL',t,a))
  if t==source.ENTRY:self.target_home=self.r[29]
 def hook(self,t):
  assert t in(CB1,CB2,CBNEG,self.syms['func_1516972C'],UNLINK,CUSTOM,EFFECT),hex(t)
  if t==EFFECT:put(self.memory,MARK,self.r[4])
  else:
   release=t in(self.syms['func_1516972C'],UNLINK,CUSTOM)
   q=self.active_queue
   effect(self.memory,self.case,q,self.r[4],release,self.target_home)
   if not release and self.case.mode&16:self.active_queue=OTHER
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=0xABCDEF01

def helper_code(rom):
 code={}
 for entry,n in HELPERS:code.update(zip(range(entry,entry+n*4,4),struct.unpack_from('>%dI'%n,rom,entry-0x14FD2B50)))
 return code

def caller_machine(rom,words,c=Case(),real=True):
 assert not c.mode&56
 initial=fixture(c);put(initial,COUNT,1,1);put(initial,SLOTS,node(c));put(initial,SLOTS+4,ALT);before=dict(initial);put(before,SLOTS+4,read(initial,QUEUE+8));wanted,calls=reference(before,replace(c,scan_count=1),real=real)
 code=helper_code(rom)if real else{};code.update(zip(range(source.ENTRY,source.ENTRY+4*len(words),4),words));code[END]=0
 m=RetireOracle(struct.unpack_from('>12I',rom,WINDOW-0x14FD2B50),initial,c,entry=WINDOW,connected=code,real=real);m.r[16]=QUEUE;m.r[18]=REGISTRY+29*52;m.r[19]=COUNT;m.r[20]=SLOTS;m.code=WindowCode(m.code,m);m.code.ends=(END,)
 return m,(wanted,[(source.ENTRY,(QUEUE,))]+calls,read(wanted,SLOTS+4))

def corpus():
 for count,timer,ticks,flags in itertools.product((0,1,0x80000000,0xFFFFFFFF),(-32768,-1,0,1,32767),(0,1,-1,0x7FFFFFFF,0x80000000),(0,1,2,255)):yield Case(count=count,timer=timer,ticks=ticks,flags=flags,selector=0)
 for selector in range(256):yield Case(selector=selector,mode=selector%8,phase=(selector&1)*8,seed=selector)
 for layout,mode,selector in itertools.product(range(6),range(64),(0,2)):yield Case(layout=layout,mode=mode,selector=selector)

def fullstate(m):return m.r,m.f,m.hi,m.lo,m.condition,m.memory,m.events,m.calls,m.visits,m.trace
