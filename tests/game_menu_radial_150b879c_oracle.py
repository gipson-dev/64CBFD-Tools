"""Independent descriptor/call model with explicit early capture and provider timing."""
import itertools,json,struct
from dataclasses import dataclass
from tools.experiments import game_menu_radial_150b879c_match as match
from tools.tests import game_menu_radial_150b879c_proof as proof
from tools.tests import test_game_point_interval_effect_match as g
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
STACK=g.STACK;put,read=g.put,g.read;ENTRY=match.ENTRY
RNG,FLOAT,DIRECTION,FACTORY,COPY=proof.RNG,proof.REAL,proof.DIRECTION,proof.FACTORY,proof.COPY
K0,K1,K2,K3,K4,K5=range(0x8009FD8C,0x8009FDA4,4);OUTPUT=0x50000

@dataclass(frozen=True)
class Case:
 actor:int=1;mode:int=0;amount:int=0;phase:int=0;fcsr:int=0;angle:int=0;slot:int=0;success:int=1;mutation:int=0
 randoms:tuple=(1,200,1,1);floats:tuple=(0x3f000000,0x3e800000)

def mapped(memory,h,raw):
 m=dict(memory)
 if raw:
  for off in range(-168,0):m[h+off]=memory[h+proof.canonical(off,True)]
 return m

def fixture(c,raw=False):
 h=STACK+c.phase;m={STACK+i:(i*17+165)&255 for i in range(-1024,1024)};m.update({OUTPUT+i:(i*11+7)&255 for i in range(256)})
 for i in range(4,15):put(m,h+4*i,0xabc00000+i)
 for off,val in ((16,g.bits(3.75)),(32,c.angle),(56,c.slot)):put(m,h+off,g.u32(val))
 for a,v in zip((K0,K1,K2,K3,K4,K5),(2.25,95.,101.,.5,.125,1.5)):put(m,a,g.bits(v))
 return mapped(m,h,raw)

def public(m):return{a:v for a,v in m.items()if not STACK-1024<=a<STACK+1024}

def rng_effect(m,c,h,i):
 if c.mutation&1 and i==0:put(m,K0,g.bits(8.5));put(m,h+8,g.bits(12.5))

def float_effect(m,c,i):
 if c.mutation&1 and i==0:put(m,K1,g.bits(96.));put(m,K2,g.bits(102.));put(m,K3,g.bits(.25))

def dir_effect(m,c,h,x,z):
 put(m,x,g.bits(7.25));put(m,z,g.bits(9.75))
 if c.mutation&2:put(m,K5,g.bits(3.5));put(m,h+56,0xabcde0fe)

def factory_effect(m,c,h,d):
 if c.success:
  for i in range(112):m[OUTPUT+0x10+i]=m[d+i]
  m[OUTPUT+0x9c]=0
 if c.mutation&4:put(m,h-4,g.bits(11.5))

def add(a,b):return g.single(g.floating(a)+g.floating(b))

def evaluate(initial,c,h=None,point=(1.25,-2.5,3.75)):
 h=STACK+c.phase if h is None else h;m=dict(initial);d=h-120;bonus=h-4;calls=[];obs=[]
 for at,v in ((0,c.actor),(4,c.mode),(8,g.bits(point[0])),(12,g.bits(point[1]))):put(m,h+at,g.u32(v))
 def field(off,v,n=4):put(m,d+off,v,n)
 def rng(i):calls.append((RNG,()));rng_effect(m,c,h,i);return c.randoms[i]
 def real(i):calls.append((FLOAT,()));float_effect(m,c,i);return c.floats[i]
 put(m,bonus,read(m,K0));field(0x1d,41,1);field(8,0xe03,2);field(0,0x200005);field(4,0)
 field(0xa,(rng(0)&15)+25,2);field(0xc,0);field(0x10,0)
 for off,val in((0x18,176),(0x19,160),(0x1a,42),(0x14,64),(0x15,11),(0x16,106),(0x17,255)):field(off,val,1)
 field(0x1b,rng(1)%71+60,1);field(0x1c,255,1);field(0x60,3,1);field(0x61,3,1)
 value=g.product(add(g.product(real(0),read(m,K1)),read(m,K2)),read(m,K3))
 field(0x28,value);field(0x2c,value)
 for i,off in enumerate((8,12,16)):field(0x30+i*4,read(m,h+off))
 for off in(0x3c,0x40,0x44):field(off,0)
 speed=g.product(add(g.product(real(1),g.bits(154.)),g.bits(205.)),read(m,K4));angle=read(m,h+34,2);angle=g.u32((angle^0x8000)-0x8000)
 calls.append((DIRECTION,(angle,speed,d+0x48,d+0x50)));dir_effect(m,c,h,d+0x48,d+0x50);field(0x4c,0);field(0x54,0)
 first=0x40 if rng(2)&1 else 0;second=0x80 if rng(3)&1 else 0;field(0x58,second|0xe05|first|0xc000)
 for off,v,n in((0x62,10,1),(0x63,255,1),(0x1e,28,2),(0x20,9,2),(0x22,25,2),(0x64,255,1),(0x65,0,1)):field(off,v,n)
 field(0x24,read(m,K5));calls.append((FACTORY,(d,1,4,read(m,h+59,1),1)));obs.append(g.packet(m,d,112));factory_effect(m,c,h,d)
 if c.success:
  calls.append((COPY,(OUTPUT+0xa8,bonus,4)))
  for i in range(4):m[OUTPUT+0xa8+i]=m[bonus+i]
 return m,calls,obs

def words(path):
 lookup={v[1]:v[2][1]for v in symbol_rows((match.FROZEN/'conker/build/conker.us.elf').read_bytes())}
 return bound_blob(*payload(path,match.NAME),lookup)

class Oracle(g.Oracle):
 def __init__(self,code,c,raw=False):
  self.cc=c;self.raw=raw;self.obs=[];self.i=self.j=0;g.Oracle.__init__(self,code,fixture(c,raw),c,entry=ENTRY);self.home=STACK+c.phase;self.r[4:8]=[g.u32(c.actor),g.u32(c.mode),g.bits(1.25),g.bits(-2.5)]
 def record_call(self,t):
  n={RNG:0,FLOAT:0,DIRECTION:4,FACTORY:5,COPY:3}[t];args=tuple(map(g.u32,self.arguments(n)));self.calls.append((t,args))
  if t==FACTORY:self.obs.append(g.packet(self.memory,args[0],112))
 def hook(self,t):
  c=self.cc;h=self.home;a=self.calls[-1][1];value=0x12345678;fvalue=None
  if t==RNG:rng_effect(self.memory,c,h,self.i);value=c.randoms[self.i];self.i+=1
  elif t==FLOAT:float_effect(self.memory,c,self.j);fvalue=c.floats[self.j];self.j+=1
  elif t==DIRECTION:dir_effect(self.memory,c,h,a[2],a[3])
  elif t==FACTORY:factory_effect(self.memory,c,h,a[0]);value=OUTPUT if c.success else 0
  elif t==COPY:
   for i in range(a[2]):self.memory[a[0]+i]=self.memory[a[1]+i]
   value=a[0]
  else:raise AssertionError(hex(t))
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.r[2]=g.u32(value)
  if fvalue is not None:self.f[0]=fvalue

def calls_normalized(calls,h,raw):
 def one(t,a):
  positions={DIRECTION:(2,3),FACTORY:(0,),COPY:(1,)}.get(t,())
  return t,tuple(h+proof.canonical(v-h,True)if raw and i in positions and h-168<=v<h else v for i,v in enumerate(a))
 return[one(t,a)for t,a in calls]

def run(state):
 one,_=match.pad_both(state);programs=((state['raw_words'],True),(state['retail_words'],False),(words(one),False));count=0;seen=set()
 for slot,angle,flags,success,mutation,phase in itertools.product((0,1,255),(0,1,127,128,255,0x7fff,0x8000,0xffff),range(4),(0,1),range(8),(0,8)):
  c=Case(slot=0xabc00000|slot,angle=0x12340000|angle,success=success,mutation=mutation,phase=phase,randoms=(angle*3,0xffffffff-angle,flags&1,flags>>1),floats=(g.bits(.125*(angle%7)),g.bits(.125*(slot%7))))
  expected,calls,obs=evaluate(fixture(c),c)
  for code,raw in programs:
   m=Oracle(code,c,raw).run();assert(public(m.memory),calls_normalized(m.calls,m.home,raw),m.obs)==(public(expected),calls,obs),(c,m.calls,calls)
   assert m.r[2]==1 and m.r[29]==STACK+phase and(m.i,m.j)==(4,2)
   if not raw:seen.update(m.visits)
  count+=1
 report=dict(passes=True,cases=count,programs=3,retail_words_visited=len(seen),early_capture_and_late_load_controls=True,incoming_home_alias_tests_guest_only=True)
 (match.OUT/'guest-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
