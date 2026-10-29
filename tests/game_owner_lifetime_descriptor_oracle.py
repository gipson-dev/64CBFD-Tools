"""Owner lifetime packet, original constructor/copy, and bounded script caller."""
from dataclasses import dataclass,replace
import struct
from tools.experiments import game_owner_lifetime_descriptor_match as source
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
OWNER,OUTPUT,MARK=0x30000,0x50000,0x70000
CREATE,ALLOC,COPY=0x15134DAC,0x15167A68,0x10022EC0
WINDOW,WINDOW_ROM,WINDOW_WORDS,END,REJECT=0x15027954,0x54E04,10,0x15029BA4,0x15029BA0
HELPERS=((CREATE,0x16225C,39),(COPY,0x22EC0,11))
PADDING=(1,2,3,9,10,11,37,49,50,51,58,59)
u32=lambda n:n&0xFFFFFFFF
signed16=lambda n:((n&65535)^32768)-32768
@dataclass(frozen=True)
class Case:
 owner:int=OWNER
 identity:int=0x87
 lifetime:int=0xABCD8001
 priority:int=0x123400E1
 arg3:int=1
 outcome:int=1
 mutation:int=0
 phase:int=0
 seed:int=0
 value:int=0x40966667
 gate:int=1

def symbols():return dict(D_800A1B70=0x800A1B70,func_15134DAC=CREATE)
def args(c):return tuple(map(u32,(c.owner,c.lifetime,c.priority,c.arg3)))
def packet(home):return home-60
def data(m,p,n):return bytes(m[u32(p+i)]for i in range(n))
def fixture(c=Case(),s=None):
 s=s or symbols();m={STACK+i:(i*17+c.seed*13+0xA5)&255 for i in range(-2048,2304)}
 for base,n in((OWNER-32,256),(OUTPUT-32,256),(MARK,32)):
  m.update({base+i:(i*29+c.seed*11+0x5A)&255 for i in range(n)})
 m[u32(c.owner+0x3B)]=c.identity&255;put(m,s['D_800A1B70'],c.value);return m
def public(m):return{a:b for a,b in m.items()if not STACK-2048<=a<STACK+2304}
def effect(m,c,s,home):
 put(m,MARK,0x13579BDF)
 if c.mutation&1:m[u32(c.owner+0x3B)]^=0x55;put(m,s['D_800A1B70'],0xBF800000)
 if c.mutation&2:
  for i in range(4):put(m,home+4*i,0xABCDEF00+i)
 if c.mutation&4:put(m,packet(home)+40,0x8001,2)
def reference(initial,c=Case(),s=None,connected=False,home=None):
 s=s or symbols();m=dict(initial);home=STACK+c.phase if home is None else home;p=packet(home)
 for i,v in enumerate(args(c)):put(m,home+4*i,v)
 identity=m[u32(c.owner+0x3B)];value=read(m,s['D_800A1B70'])
 put(m,p,identity,1);put(m,p+4,c.owner);put(m,p+8,3,1)
 for off in(12,16,20,24):put(m,p+off,0)
 put(m,p+28,value);put(m,p+32,0x41080000);put(m,p+36,2,1)
 for off,v in((38,40),(40,16),(42,c.lifetime),(44,0)):put(m,p+off,v,2)
 for off,v in((46,5),(47,8),(48,255),(56,0),(57,255)):put(m,p+off,v,1)
 put(m,p+52,0x3F800000);packets=[data(m,p,60)];calls=[(s['func_15134DAC'],(p,0))];copies=[]
 if connected:calls.append((ALLOC,(41,0,128,1,255,1)))
 effect(m,c,s,home);answer=OUTPUT if c.outcome else 0
 if connected and answer:
  calls.append((COPY,(OUTPUT+24,p,60)));copies.append(data(m,p,60))
  for i,b in enumerate(copies[-1]):m[OUTPUT+24+i]=b
  put(m,OUTPUT+84,-signed16(read(m,p+40,2)),2);put(m,OUTPUT+16,1);put(m,OUTPUT+20,0)
  for off in(112,116,120):put(m,OUTPUT+off,0)
 return m,calls,answer,packets,copies
class LifetimeOracle(FactoryOracle):
 def __init__(self,words,memory,c=Case(),entry=None,s=None,connected=None):
  super().__init__(words,memory,c,entry=source.ENTRY if entry is None else entry,s=s or symbols(),connected=connected,arguments=args(c))
  self.packets=[];self.copies=[]
 def record_call(self,t):
  counts={source.ENTRY:4,self.syms['func_15134DAC']:2,ALLOC:6,COPY:3};assert t in counts,hex(t)
  a=tuple(map(u32,self.arguments(counts[t])));self.calls.append((t,a));self.events.append(('CALL',t,a))
  if t==source.ENTRY:self.target_home=self.r[29]
  if t==self.syms['func_15134DAC']:self.packets.append(data(self.memory,a[0],60))
  if t==COPY:self.copies.append(data(self.memory,a[1],a[2]))
 def hook(self,t):
  assert t in(self.syms['func_15134DAC'],ALLOC),hex(t)
  effect(self.memory,self.case,self.syms,self.target_home)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=OUTPUT if self.case.outcome else 0

def helper_code(rom):
 code={}
 for entry,offset,n in HELPERS:code.update(zip(range(entry,entry+n*4,4),struct.unpack_from('>%dI'%n,rom,offset)))
 return code

def caller_machine(rom,words,c=Case(),connected=True):
 c=replace(c,lifetime=signed16(c.lifetime),priority=c.priority&255,arg3=1);initial=fixture(c);home=STACK+c.phase
 put(initial,home+0x764,c.owner);put(initial,home+0x662,c.lifetime,2);put(initial,home+0x773,c.priority,1)
 code=helper_code(rom)if connected else{};code.update(zip(range(source.ENTRY,source.ENTRY+len(words)*4,4),words));code[END]=code[REJECT]=0
 m=LifetimeOracle(struct.unpack_from('>10I',rom,WINDOW_ROM),initial,c,entry=WINDOW,connected=code);m.r[3]=u32(c.gate);m.before=m.r[:];m.code=WindowCode(m.code,m);m.code.ends=(END,REJECT)
 if c.owner and c.gate>0:
  wanted=reference(initial,c,connected=connected,home=home);expected,calls,value,packets,copies=wanted
  return m,(expected,[(source.ENTRY,args(c))]+calls,1,packets,copies),END
 if not c.owner:return m,(initial,[],1,[],[]),END
 return m,(initial,[],m.r[2],[],[]),REJECT

def state(m):return(m.r,m.f,m.hi,m.lo,m.condition,m.memory,m.events,m.calls,m.visits,m.trace,m.packets,m.copies)
