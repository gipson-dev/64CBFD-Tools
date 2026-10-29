"""Phase-pair callback: float order, saved state and original caller/helpers."""
from dataclasses import dataclass,replace
import itertools,math,struct
from tools.experiments import game_owner_phase_pair_match as source
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_animation_timeline_oracle import bits,floating,signed
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests import test_game_trig_match as trig
from tools.tests.test_game_sine_phase_update import wrap
from tools.tests import test_game_actor_burst_consumer_match as faults
OWNER,OTHER,THIRD,MARK,LOOKUP=0x30000,0x50000,0x60000,0x70000,0x71000
CLOCK,BOUND,TICKS,GATE,TABLEPTR,TABLE=0x800BE9A4,0x800A56A4,0x800BE9E4,0x800C35EA,0x800C3958,0x80089C18
SINE,WRAP,TIMER,VALUE,RELEASE=0x15047D60,0x15144B68,0x15108B80,0x15108BC0,0x1516972C
HELPERS=((SINE,0x75210,104),(WRAP,0x172018,24),(TIMER,0x136030,16),(VALUE,0x136070,30))
u32=lambda x:x&0xFFFFFFFF
@dataclass(frozen=True)
class Case:
 phases:tuple=(bits(1.25),bits(-2.5))
 clock:int=bits(1.)
 scales:tuple=(0x3DAF837B,0x3DA05BC0,0x40E35C2A,0x40E35C2A)
 results:tuple=(bits(.25),bits(-.5),bits(1.5),bits(-2.5))
 offset:int=0
 mode:int=0
 alias:object=None
 phase:int=0
 index:int=2
 timer:int=3
 ticks:int=1
 gate:int=1
 seed:int=0

def symbols():return dict(sinf=SINE,func_15144B68=WRAP,func_15108B80=TIMER,func_15108BC0=VALUE,D_800BE9A4=CLOCK,**{'D_%08X'%a:a for a in range(0x800A2470,0x800A2480,4)})
def owner(c,s):return OWNER if c.alias is None else u32(s['D_800BE9A4']-c.offset-0xF8-c.alias)
def state(m,p):return u32(p+signed(read(m,p+0x50))+0xF8)
def fixture(c=Case(),s=None):
 s=symbols()if s is None else s;p=owner(c,s);m={STACK+i:(i*17+c.seed*13+0xA5)&255 for i in range(-2048,1024)}
 for base,n in((p-16,0x800),(OTHER-16,0x800),(THIRD-16,0x800),(MARK,32),(LOOKUP-0x88,0x200)):
  for i in range(n):m.setdefault(u32(base+i),(i*29+c.seed+0x5A)&255)
 for at,value in trig.GLOBALS.items():put(m,at,value)
 put(m,BOUND,0x40C90FDB);put(m,TICKS,c.ticks);m[GATE]=c.gate;put(m,TABLEPTR,LOOKUP)
 for b in(p,OTHER,THIRD):
  put(m,b+0x50,c.offset);q=state(m,b)
  for off,val in((0,bits(99.)),(4,bits(-99.)),(8,c.phases[0]),(12,c.phases[1]),(16,bits(226.)),(20,c.index),(28,c.timer)):put(m,q+off,val)
 for i in range(-2,5):put(m,LOOKUP+i*0x44+4,bits(i*.25+10.))
 for name,value in zip(('D_800A2470','D_800A2474','D_800A2478','D_800A247C'),c.scales):put(m,s[name],value)
 put(m,s['D_800BE9A4'],c.clock);return m

def public(m):return{a:b for a,b in m.items()if not STACK-2048<=a<STACK+1024}
def add(a,b):return bits(floating(a)+floating(b))
def mul(a,b):return bits(floating(a)*floating(b))
def effects(m,c,p,q,s,n,home):
 if n==1 and c.mode&1:put(m,q+12,bits(2.));put(m,p+0x50,0x400);put(m,s['D_800A2478'],bits(3.))
 if n==2 and c.mode&2:put(m,q+8,bits(-.75));put(m,s['D_800A247C'],bits(-3.))
 if n==3 and c.mode&4:put(m,q+12,bits(3.25));put(m,s['D_800A2478'],bits(4.))
 if n==4 and c.mode&8:put(m,s['D_800A247C'],bits(.5))
 if n==1 and c.mode&16:put(m,home,OTHER)
 if n==5 and c.mode&32:put(m,home,THIRD)
def tail(m,arg,t):
 q=state(m,arg)
 if t==TIMER:
  if read(m,q+20)!=999:
   result=u32(read(m,q+28)-read(m,TICKS));put(m,q+28,result)
   if signed(result)<0:put(m,q+20,999)
 else:
  index=read(m,q+20);result=bits(226.)if index==999 or m[GATE]!=1 else read(m,u32(read(m,TABLEPTR)+signed(index)*0x44+4))
  put(m,q+16,result)
def reference(initial,c=Case(),s=None,real=False,home=None):
 s=symbols()if s is None else s;m=dict(initial);p=owner(c,s);q=state(m,p);home=STACK+c.phase if home is None else home;calls=[]
 def call(name,arg):
  t=s[name];calls.append((t,arg));n=len(calls)
  if n<=4:result=(trig.reference(arg)if name=='sinf'else wrap(arg))if real else c.results[n-1]
  elif real:tail(m,arg,TIMER if name=='func_15108B80'else VALUE);result=0
  else:put(m,arg+0x30+(n-5),0x80+n,1);result=0
  if not real:effects(m,c,p,q,s,n,home)
  return result
 first=add(read(m,q+8),mul(read(m,s['D_800A2470']),read(m,s['D_800BE9A4'])));second=read(m,q+12)
 put(m,q+8,first);put(m,q+12,add(second,mul(read(m,s['D_800A2474']),read(m,s['D_800BE9A4']))))
 put(m,q+8,call('func_15144B68',read(m,q+8)));put(m,q+12,call('func_15144B68',read(m,q+12)))
 x=call('sinf',read(m,q+8));put(m,q,mul(x,read(m,s['D_800A2478'])))
 y=call('sinf',read(m,q+12));put(m,q+4,mul(y,read(m,s['D_800A247C'])))
 active=OTHER if not real and c.mode&16 else p;call('func_15108B80',active)
 active=THIRD if not real and c.mode&32 else active;call('func_15108BC0',active)
 return m,calls,1

def corpus():
 for i in range(256):
  yield Case(phases=(bits((i%17-8)*.25),bits((i%23-11)*.5)),clock=bits((0.,-0.,.125,-.25,1.,-1.,4.,2.)[i%8]),offset=(-128,0,256)[i%3],mode=i%64,phase=(i%2)*8,seed=i)
 for alias,mode,clock in itertools.product((0,4,8,12), (0,15,16,32,63),(0.,1.)):yield Case(alias=alias,mode=mode,clock=bits(clock))
 for word,field in itertools.product((1,0x80000001,0x7F800000,0xFF800000,0x7FC12345),range(2)):
  v=list(Case().phases);v[field]=word;yield Case(phases=tuple(v))
class PhaseOracle(FactoryOracle):
 def __init__(self,words,memory,c=Case(),entry=None,s=None,connected=None,real=False):
  self.targets=symbols()if s is None else s;self.real=real;self.owner_pointer=owner(c,self.targets);self.saved_state=state(memory,self.owner_pointer);self.home=STACK+c.phase;self.ordinal=0
  super().__init__(words,memory,c,entry=source.ENTRY if entry is None else entry,s=self.targets,connected=connected,arguments=(self.owner_pointer,))
 def execute(self,word):
  op,rs,rt,rd,fd,fn=word>>26,word>>21&31,word>>16&31,word>>11&31,word>>6&31,word&63
  if op==0 and fn==3:self.r[rd]=u32(signed(self.r[rt])>>fd)
  elif op==17 and rs==16 and fn==13:self.f[fd]=u32(math.trunc(floating(self.f[rd])))
  elif op==17 and rs==16 and fn==7:self.f[fd]=self.f[rd]^0x80000000
  else:super().execute(word)
  self.r[0]=0
 def record_call(self,t):
  if t==source.ENTRY:self.home=self.r[29];arg=self.r[4]
  elif t==RELEASE:arg=self.r[4]
  else:
   assert t in self.targets.values(),hex(t)
   arg=self.f[12]if t in(self.targets['sinf'],self.targets['func_15144B68'])else self.r[4];self.ordinal+=1
  self.calls.append((t,arg));self.events.append(('CALL',t,arg))
 def hook(self,t):
  if t==RELEASE:put(self.memory,MARK,self.r[4]);value=0
  else:
   assert t in(self.targets['sinf'],self.targets['func_15144B68'],self.targets['func_15108B80'],self.targets['func_15108BC0'])
   if self.ordinal<=4:value=self.case.results[self.ordinal-1]
   else:put(self.memory,self.r[4]+0x30+(self.ordinal-5),0x80+self.ordinal,1);value=0
   effects(self.memory,self.case,self.owner_pointer,self.saved_state,self.targets,self.ordinal,self.home)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.f[0]=value;self.hi,self.lo=0xA5000010,0xA5000011

def helper_code(rom):
 result={}
 for entry,offset,n in HELPERS:result.update(zip(range(entry,entry+4*n,4),struct.unpack_from('>%dI'%n,rom,offset)))
 return result

def caller_machine(rom,words,c=Case(),flags=0,lifetime=10,index=0,real=False):
 m=fixture(c);p=owner(c,symbols());m[p+0x10]=flags;m[p+0x11]=index&255;put(m,p+0x14,lifetime,2);put(m,TABLE,source.ENTRY)
 before=dict(m);expired=False
 if flags&1:
  remaining=(lifetime-c.ticks)&65535;put(before,p+0x14,remaining,2);expired=bool(remaining&0x8000)
 if expired:put(before,MARK,p);calls=[(RELEASE,p)]
 elif index==-1:calls=[]
 else:
  before,inner,_=reference(before,c,real=real,home=STACK+c.phase-32);calls=[(source.ENTRY,p)]+inner
 code=helper_code(rom)if real else{};code.update(zip(range(source.ENTRY,source.ENTRY+4*len(words),4),words))
 model=PhaseOracle(struct.unpack_from('>41I',rom,0x168C48),m,c,entry=source.CALLER,connected=code,real=real)
 return model,(public(before),calls)

def fullstate(m):return m.r,m.f,m.hi,m.lo,m.condition,m.memory,m.events,m.calls,m.visits,m.trace
