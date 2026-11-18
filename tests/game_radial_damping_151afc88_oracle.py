"""Private independent guest screen; inputs and helper behavior are bounded."""
import sys,struct,json,itertools
from dataclasses import dataclass
from pathlib import Path
from tools.experiments import game_radial_damping_151afc88_match as match
root=match.ROOT;p=match.OUT
from tools.pad_generated_object import parse_object
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests import test_game_point_interval_effect_match as g
STACK=g.STACK;put,read=g.put,g.read
RNG=0x150ADA20;FLOAT=0x150ADA68;DIRECTION=0x15143794;FACTORY=0x15130374;COPY=0x10022ec0;K0,K1,K2=0x800aa114,0x800aa118,0x800aa11c;OUTPUT=0x50000;ENTRY=0x151afc88
AMPLITUDE=0x800AA110
sym={v[1]:v[2][1] for v in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())}
def words(path):
 d,f,r=parse_object(path);at=f['func_151AFC88']['value'];n=f['func_151AFC88']['size'];refs={k-at:v for k,v in r.items() if at<=k<at+n};return bound_blob(d[at:at+n],refs,sym)
@dataclass(frozen=True)
class Case:
 actor:int=1;mode:int=0;amount:int=0;phase:int=0;fcsr:int=0;angle:int=0;slot:int=0;success:int=1;mutation:int=0;randoms:tuple=(1,200,37,1,1);floats:tuple=(0x3f000000,0x3e800000)
def fixture(c):
 h=STACK+c.phase;m={STACK+i:(i*17+165)&255 for i in range(-1024,1024)};m.update({OUTPUT+i:(i*11+7)&255 for i in range(256)})
 for off,val in ((16,g.bits(3.75)),(32,c.angle),(56,c.slot)):put(m,h+off,g.u32(val))
 put(m,AMPLITUDE,g.bits(202.))
 for a,v in ((K0,g.bits(.5)),(K1,g.bits(1.5)),(K2,g.bits(2.25))):put(m,a,v)
 return m
def public(m):return {a:b for a,b in m.items() if not STACK-1024<=a<STACK+1024}
def rng_effect(m,c,h,index):
 if c.mutation&1 and index==1:put(m,h+8,g.bits(12.5))
def dir_effect(m,c,h,q):
 for i,v in enumerate((g.bits(7.25),g.bits(-8.5),g.bits(9.75))):put(m,q+4*i,v)
 if c.mutation&2:put(m,K1,g.bits(3.5));put(m,K2,g.bits(4.25));put(m,h+56,0xabcde0fe)
def factory_effect(m,c,h):
 if c.success:
  for i in range(112):m[OUTPUT+0x10+i]=m[h-0x74+i]
  m[OUTPUT+0x9c]=0
 if c.mutation&4:put(m,h-0x7c,g.bits(8.5))
def fladd(a,b):return g.single(g.floating(a)+g.floating(b))
def reference(initial,c):
 m=dict(initial);h=STACK+c.phase;d=h-0x74;bonus=h-0x7c;calls=[];obs=[]
 for at,v in ((0,c.actor),(4,c.mode),(8,g.bits(1.25)),(12,g.bits(-2.5))):put(m,h+at,g.u32(v))
 def field(off,v,n=4):put(m,d+off,v,n)
 def rng(i):calls.append((RNG,()));rng_effect(m,c,h,i);return c.randoms[i]
 field(0x1d,41,1);field(8,0xe03,2);field(0,0x200005);field(4,0);r=rng(0);field(0xa,(r&15)+25,2);field(0xc,0);field(0x10,0)
 for off,val in ((0x18,176),(0x19,160),(0x1a,42),(0x14,64),(0x15,11),(0x16,106),(0x17,255)):field(off,val,1)
 r=rng(1);field(0x1b,r%156+100,1);field(0x1c,255,1);field(0x60,3,1);field(0x61,3,1);calls.append((FLOAT,()))
 for i,off in enumerate((8,12,16)):field(0x30+i*4,read(m,h+off))
 v=fladd(g.product(c.floats[0],g.bits(202.)),g.bits(101.));field(0x28,v);field(0x2c,v);r=rng(2);calls.append((FLOAT,()))
 scale=g.product(fladd(g.product(c.floats[1],read(m,AMPLITUDE)),g.bits(500.)),read(m,K0));signed=lambda v:g.u32(((v&0xffff)^0x8000)-0x8000)
 a=(signed(read(m,h+34,2)),signed((r%21)-20),scale,d+0x48);calls.append((DIRECTION,a));dir_effect(m,c,h,d+0x48);field(0x58,0xe05);field(0x54,0)
 if rng(3)&1:field(0x58,read(m,d+0x58)|0x40)
 if rng(4)&1:field(0x58,read(m,d+0x58)|0x80)
 field(0x62,6,1);field(0x63,255,1);field(0x1e,15,2);field(0x20,17,2);field(0x22,25,2);field(0x24,read(m,K1));put(m,bonus,read(m,K2))
 a=(d,1,4,read(m,h+59,1),1);calls.append((FACTORY,a));obs.append(g.packet(m,d,112));factory_effect(m,c,h)
 if c.success:
  calls.append((COPY,(OUTPUT+0xa8,bonus,4)))
  for i in range(4):m[OUTPUT+0xa8+i]=m[bonus+i]
 return public(m),calls,obs
class Oracle(g.Oracle):
 def __init__(self,code,c):
  self.cc=c;self.obs=[];self.i=self.j=0;g.Oracle.__init__(self,code,fixture(c),c,entry=ENTRY);self.home=STACK+c.phase;self.r[4:8]=[g.u32(c.actor),g.u32(c.mode),g.bits(1.25),g.bits(-2.5)]
 def record_call(self,t):
  counts={RNG:0,FLOAT:0,DIRECTION:4,FACTORY:5,COPY:3};assert t in counts,hex(t);a=tuple(map(g.u32,self.arguments(counts[t])));self.calls.append((t,a))
  if t==FACTORY:self.obs.append(g.packet(self.memory,a[0],112))
 def hook(self,t):
  c=self.cc;h=self.home;a=self.calls[-1][1];value=0x12345678;fvalue=None
  if t==RNG:rng_effect(self.memory,c,h,self.i);value=c.randoms[self.i];self.i+=1
  elif t==FLOAT:fvalue=c.floats[self.j];self.j+=1
  elif t==DIRECTION:dir_effect(self.memory,c,h,a[3])
  elif t==FACTORY:factory_effect(self.memory,c,h);value=OUTPUT if c.success else 0
  elif t==COPY:
   for i in range(a[2]):self.memory[a[0]+i]=self.memory[a[1]+i]
   value=a[0]
  else:raise AssertionError(hex(t))
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.r[2]=g.u32(value)
  if fvalue is not None:self.f[0]=fvalue
def run(state):
 one,_=match.pad_both(state);raw,retail,patched=state['raw_words'],state['retail_words'],words(one);assert retail==patched
 count=0;seen=set()
 for slot,angle,flags,success,mutation,phase in itertools.product((0,1,255),(0,1,127,128,255,0x7fff,0x8000,0xffff),range(4),(0,1),range(8),(0,8)):
  c=Case(slot=0xabc00000|slot,angle=0x12340000|angle,success=success,mutation=mutation,phase=phase,randoms=(angle*3,0xffffffff-angle,angle*11,flags&1,flags>>1),floats=(g.bits(.125*(angle%7)),g.bits(.125*(slot%7))))
  expected=reference(fixture(c),c)
  complete=[]
  for code in (raw,retail,patched):
   m=Oracle(code,c).run();assert (public(m.memory),m.calls,m.obs)==expected,(c,m.calls,expected[1]);assert m.r[2]==1 and m.r[29]==STACK+phase
   complete.append((m.memory,m.r,m.f))
   if code is retail:seen.update(m.visits)
  assert all(value==complete[0]for value in complete)
  count+=1
 result=dict(cases=count,bodies=3,retail_words_visited=len(seen),bounded_helpers=True,static_instruction_and_packet_model=True)
 return result

def home_alias(state):
 class Changed(Oracle):
  def hook(self,t):
   super().hook(t)
   if t==RNG and self.i==3:put(self.memory,self.home+32,0x12348001)
 one,_=match.pad_both(state);c=Case(angle=42);values=[]
 for code in (state['raw_words'],state['retail_words'],words(one)):
  machine=Changed(code,c).run();values.append([a[0] for t,a in machine.calls if t==DIRECTION][0])
 return values
