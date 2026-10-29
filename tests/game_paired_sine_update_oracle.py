"""Paired sine update: ordered float32 accesses and bounded original callbacks."""
from dataclasses import dataclass,replace
import itertools,math,struct
from tools.experiments import game_paired_sine_update_match as source
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_animation_timeline_oracle import bits,floating,signed
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests import test_game_trig_match as trig
from tools.tests.test_game_sine_phase_update import wrap
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
OWNER,OTHER,CONTEXT,TABLE,BOUND=0x30000,0x50000,0x60000,0x80089760,0x800A56A4
WINDOW,END,WINDOW_WORDS=0x15130A0C,0x15130A50,17
OFFSETS=tuple(range(0xA8,0xD0,4))
HELPERS=((source.SINE,0x75210,104),(source.WRAP,0x172018,24))
@dataclass(frozen=True)
class Case:
 fields:tuple=tuple(bits(x)for x in(99.,-99.,1.25,-2.5,2.,-3.,.5,-.25,.125,.75))
 clock:int=bits(1.)
 results:tuple=tuple(bits(x)for x in(.25,-.5,1.5,2.5))
 mode:int=0
 alias:object=None
 phase:int=0
 context:int=CONTEXT
 seed:int=0
def symbols():return dict(sinf=source.SINE,func_15144B68=source.WRAP,D_800BE9A4=source.CLOCK)
def address(c,s):return OWNER if c.alias is None else(s['D_800BE9A4']-c.alias)&0xFFFFFFFF
def fixture(c=Case(),s=None):
 s=symbols()if s is None else s;p=address(c,s);m={STACK+i:(i*17+c.seed*13+0xA5)&255 for i in range(-2048,1024)}
 for base,n in((p-16,0x110),(OTHER-16,0x110),(CONTEXT,64),(s['D_800BE9A4']-16,36)):
  for i in range(n):m.setdefault(base+i,(i*29+c.seed+0x5A)&255)
 for at,value in trig.GLOBALS.items():put(m,at,value)
 put(m,BOUND,0x40C90FDB)
 for base in(p,OTHER):
  for off,value in zip(OFFSETS,c.fields):put(m,base+off,value)
 put(m,s['D_800BE9A4'],c.clock);return m
def public(m):return{a:b for a,b in m.items()if not STACK-2048<=a<STACK+1024}
def add(a,b):return bits(floating(a)+floating(b))
def mul(a,b):return bits(floating(a)*floating(b))
def effects(m,c,p,s,ordinal,home):
 if ordinal==1 and c.mode&1:
  for off,value in((0xC4,2.),(0xB8,7.),(0xB0,-4.)):put(m,p+off,bits(value))
  put(m,s['D_800BE9A4'],bits(2.))
 if ordinal==1 and c.mode&8:put(m,home,OTHER)
 active=OTHER if c.mode&8 and ordinal>1 else p
 if ordinal==2 and c.mode&2:
  for off,value in((0xB4,11.),(0xBC,-5.),(0xC8,.5),(0xCC,-.25)):put(m,active+off,bits(value))
  put(m,s['D_800BE9A4'],bits(.5))
 if ordinal==3 and c.mode&4:
  put(m,active+0xC4,bits(3.25));put(m,active+0xA8,bits(17.));put(m,s['D_800BE9A4'],bits(-2.))
def reference(initial,c=Case(),s=None,real=False,home=None):
 s=symbols()if s is None else s;m=dict(initial);p=address(c,s);home=STACK+c.phase if home is None else home;calls=[]
 def call(name,arg):
  calls.append((s[name],arg));n=len(calls)
  value=(trig.reference(arg)if name=='sinf'else wrap(arg))if real else c.results[n-1]
  if not real:effects(m,c,p,s,n,home)
  return value
 first=call('sinf',read(m,p+0xC0));active=OTHER if not real and c.mode&8 else p
 second=call('sinf',read(m,active+0xC4))
 # Both output expressions are evaluated before the first output store.
 x=add(read(m,active+0xB0),mul(read(m,active+0xB8),first));y=add(read(m,active+0xB4),mul(read(m,active+0xBC),second))
 put(m,active+0xA8,x);put(m,active+0xAC,y)
 x=add(read(m,active+0xC0),mul(read(m,active+0xC8),read(m,s['D_800BE9A4'])));put(m,active+0xC0,x)
 y=add(read(m,active+0xC4),mul(read(m,active+0xCC),read(m,s['D_800BE9A4'])));put(m,active+0xC4,y)
 put(m,active+0xC0,call('func_15144B68',read(m,active+0xC0)))
 put(m,active+0xC4,call('func_15144B68',read(m,active+0xC4)))
 return m,calls,1
def corpus():
 vals=(0.,-0.,1.75,-2.75,16777216.,-16777216.,1e20,-1e20)
 for i in range(256):
  fields=tuple(bits(vals[(i+j)%8])for j in range(6))+tuple(bits((i%17-8)*.25+j*.125)for j in range(4))
  yield Case(fields=fields,clock=bits((0.,-0.,.125,-.25,1.,-1.,4.,2.)[i%8]),mode=i%16,context=(0,CONTEXT,0xFFFFFFFF,0x80000000)[i%4],seed=i)
 for field,value,mode in itertools.product(range(10),(1,0x80000001,0x7F800000,0xFF800000,0x7FC12345,0x7FA12345),(0,7)):
  fields=list(Case().fields);fields[field]=value;yield replace(Case(),fields=tuple(fields),mode=mode)
 for alias,mode,clock in itertools.product(OFFSETS,range(8),(0.,1.)):yield Case(alias=alias,mode=mode,clock=bits(clock))
 for mode,phase,context in itertools.product(range(16),(0,8),(0,CONTEXT,0xFFFFFFFF)):yield Case(mode=mode,phase=phase,context=context)
class SineOracle(TimingOracle):
 def __init__(self,words,memory,c=Case(),entry=None,s=None,connected=None,real=False):
  self.case=c;self.targets=symbols()if s is None else s;self.real=real;self.record=address(c,self.targets);self.home=STACK+c.phase
  super().__init__(words,memory,phase=c.phase,entry=source.ENTRY if entry is None else entry,arguments=(self.record,c.context),connected=connected)
  self.trace=[];self.all_accesses=0;self.cut=None
 def execute(self,word):
  op,rs,rt,rd,fd,fn=word>>26,word>>21&31,word>>16&31,word>>11&31,word>>6&31,word&63
  if op==0 and fn==3:self.r[rd]=signed(self.r[rt])>>fd&0xFFFFFFFF
  elif op==32:
   prior=self.own_instruction;self.own_instruction=True;self.dispatched_word=word
   try:
    offset=((word&65535)^32768)-32768;value=self.get((self.r[rs]+offset)&0xFFFFFFFF,1);self.r[rt]=((value^128)-128)&0xFFFFFFFF
   finally:self.own_instruction=prior
  elif op==17 and rs==16 and fn==13:self.f[fd]=math.trunc(floating(self.f[rd]))&0xFFFFFFFF
  elif op==17 and rs==16 and fn==7:self.f[fd]=self.f[rd]^0x80000000
  else:super().execute(word)
  self.r[0]=0
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
  if t==source.ENTRY:self.home=self.r[29];arg=tuple(self.arguments(2))
  else:assert t in(self.targets['sinf'],self.targets['func_15144B68']),hex(t);arg=self.f[12]
  self.calls.append((t,arg));self.events.append(('CALL',t,arg))
 def hook(self,t):
  assert t in(self.targets['sinf'],self.targets['func_15144B68']);n=sum(t in(self.targets['sinf'],self.targets['func_15144B68'])for t,_ in self.calls)
  result=(trig.reference(self.f[12])if t==self.targets['sinf']else wrap(self.f[12]))if self.real else self.case.results[n-1]
  if not self.real:effects(self.memory,self.case,self.record,self.targets,n,self.home)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.f[0]=result;self.hi,self.lo=0xA5000010,0xA5000011
def helper_code(rom):
 result={}
 for entry,pos,n in HELPERS:result.update(zip(range(entry,entry+4*n,4),struct.unpack_from('>%dI'%n,rom,pos)))
 return result
def caller_machine(rom,words,c=Case(),index=11,gate=0,real=False,connected_helpers=False):
 m=fixture(c);p=address(c,symbols());m[p+0x72]=index&255
 for i in range(160):m[TABLE+i]=rom[0x22E220+i]
 home=STACK+c.phase;code=helper_code(rom)if connected_helpers else{};code.update(zip(range(source.ENTRY,source.ENTRY+4*len(words),4),words));code[END]=0
 machine=SineOracle(struct.unpack_from('>17I',rom,WINDOW-0x15000000+0x2D4B0),m,c,entry=WINDOW,connected=code,real=real);machine.r[7]=gate;machine.before=machine.r[:];machine.code=WindowCode(machine.code,machine);machine.code.ends=(END,)
 wanted=reference(m,c,real=real,home=home)if index==11 and gate==0 else(m,[],None)
 calls=[(source.ENTRY,(p,home+0x48))]+wanted[1]if index==11 and gate==0 else[]
 return machine,(public(wanted[0]),calls,gate,p)
