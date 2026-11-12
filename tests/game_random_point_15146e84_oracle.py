"""Bounded guest reference for the randomized actor-point effect callback."""
import itertools
from dataclasses import dataclass
from tools.experiments import game_random_point_15146e84_match as match
from tools.tests import test_game_point_interval_effect_match as g
from tools.pad_generated_object import parse_object
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
ENTRY=0x15146E84;SELECT=0x15146890;SLOT=0x151D8E20;EXTRA=0x15142180;RNG=0x150ADA20;FLOAT=0x150ADA68;WIDE=0x151D9B8C;SIMPLE=0x151DAB58
ACTOR,STACK=g.ACTOR,g.STACK
put,read=g.put,g.read

def words(path):
 d,f,r=parse_object(path);at=f[match.NAME]['value'];n=f[match.NAME]['size'];refs={k-at:v for k,v in r.items() if at<=k<at+n}
 syms={v[1]:v[2][1] for v in symbol_rows((match.ROOT/'conker/build/conker.us.elf').read_bytes())}
 return tuple(bound_blob(d[at:at+n],refs,syms))

@dataclass(frozen=True)
class Case:
 active:int=0x50000;mode:int=1;amount:int=71;answer:int=1;slot:int=10;randoms:tuple=(1,100,40);sample:int=0x3f000000;mutation:int=0;phase:int=0;fcsr:int=0;actor:int=ACTOR

def fixture(c):
 m={STACK+i:(i*17+165)&255 for i in range(-1024,1024)};m.update({c.actor+i:(i*13+91)&255 for i in range(0x340)});put(m,c.actor+0x1d4,c.active);return m

def select_effect(m,c,h):
 if c.mutation&1:put(m,h+8,0xffffff85)
def slot_effect(m,c,h):
 if c.mutation&2:put(m,h+8,71)
def extra_effect(m,c,h,p,r):
 if c.mutation&4:put(m,p,g.bits(-17.5));put(m,p+8,g.bits(12.5));put(m,r,g.bits(99.));put(m,r+0x18,0x76543210);put(m,h-0x31,0x45,1)
def random_effect(m,c,h,r,q):
 if c.mutation&8:put(m,q,g.bits(18.5));put(m,r+4,0x1234,2);put(m,h-0x31,0x46,1)
def public(m):return {a:b for a,b in m.items() if not STACK-1024<=a<STACK+1024}
def reference(initial,c,home=None):
 m=dict(initial);h=STACK+c.phase if home is None else home;p=h-12;r=h-48;q=h-64;calls=[];obs=[]
 for off,val in ((0,c.actor),(4,c.mode),(8,c.amount)):put(m,h+off,g.u32(val))
 if read(m,c.actor+0x1d4):
  calls.append((SELECT,(p,c.actor,r,c.mode&255)));g.fill(m,p,r);select_effect(m,c,h)
  if c.answer:
   calls.append((SLOT,()));slot_effect(m,c,h);put(m,h-0x31,c.slot,1)
   if g.signed(read(m,h+8))>=71:
    calls.append((EXTRA,(c.slot&255,p,read(m,r+0x18),g.bits(1.),g.bits(1.))));obs.append((EXTRA,g.packet(m,p,12),read(m,r+0x18)));extra_effect(m,c,h,p,r)
   put(m,q,read(m,p));put(m,q+4,read(m,r));put(m,q+8,read(m,p+8))
   calls.append((RNG,()));random_effect(m,c,h,r,q);branch=c.randoms[0]&1
   calls.append((FLOAT,()));calls.append((RNG,()));random_effect(m,c,h,r,q)
   if branch:calls.append((RNG,()));random_effect(m,c,h,r,q)
   factor,addition=(10.,10.) if branch else (8.,5.)
   scale=g.single(g.floating(g.product(c.sample,g.bits(factor)))+addition)
   slot=read(m,h-0x31,1);arg=(c.randoms[1]%101+100)&255
   if branch:a=(slot,scale,arg,r+4,q,c.randoms[2]%41+80,1,1,0,255,1);target=WIDE
   else:a=(slot,scale,arg,q,1,255,1);target=SIMPLE
   calls.append((target,a));obs.append((target,g.packet(m,q,12),g.packet(m,r+4,18) if branch else b''))
 return public(m),calls,obs

class Oracle(g.Oracle):
 def __init__(self,code,c):
  self.cc=c;self.obs=[];self.random_index=0;g.Oracle.__init__(self,code,fixture(c),c,entry=ENTRY);self.home=STACK+c.phase
 def record_call(self,t):
  counts={SELECT:4,SLOT:0,EXTRA:5,RNG:0,FLOAT:0,WIDE:11,SIMPLE:7};assert t in counts,hex(t)
  a=tuple(map(g.u32,self.arguments(counts[t])));self.calls.append((t,a))
  if t==EXTRA:self.obs.append((EXTRA,g.packet(self.memory,a[1],12),a[2]));self.assert_control()
  if t in (WIDE,SIMPLE):
   q=a[4] if t==WIDE else a[3];self.obs.append((t,g.packet(self.memory,q,12),g.packet(self.memory,a[3],18) if t==WIDE else b''));self.assert_control()
 def hook(self,t):
  c=self.cc;a=self.calls[-1][1];h=self.home;p=h-12;r=h-48;q=h-64;value=0x12345678;fvalue=None
  if t==SELECT:g.fill(self.memory,a[0],a[2]);select_effect(self.memory,c,h);value=c.answer
  elif t==SLOT:slot_effect(self.memory,c,h);value=c.slot
  elif t==EXTRA:extra_effect(self.memory,c,h,p,r)
  elif t==RNG:random_effect(self.memory,c,h,r,q);value=c.randoms[self.random_index];self.random_index+=1
  elif t==FLOAT:fvalue=c.sample
  else:assert t in (WIDE,SIMPLE)
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.r[2]=g.u32(value)
  if fvalue is not None:self.f[0]=fvalue

def run(state):
 one,_=match.pad_both(state);raw,retail,padded=state['raw_words'],state['retail_words'],words(one);assert raw==retail==padded
 cases=[]
 for mode,active,answer,amount,branch,phase in itertools.product(range(256),(0,0x50000),(0,1),(70,71),(0,1),(0,8)):
  cases.append(Case(mode=0xabcd0000|mode,active=active,answer=answer,amount=amount,phase=phase,mutation=(0,1,2,4,8,15)[mode%6],slot=(0,1,10,255)[mode%4],randoms=(branch,(mode*0x1234567)&0xffffffff,(mode*0x7654321)&0xffffffff),sample=g.bits((mode%11)/10.)))
 seen=set()
 for c in cases:
  want,calls,obs=reference(fixture(c),c)
  for code in (raw,retail,padded):
   m=Oracle(code,c).run();m.assert_control();assert (public(m.memory),m.calls,m.obs)==(want,calls,obs),(c,m.calls,calls,m.obs,obs);assert m.r[29]==STACK+c.phase
   if code is retail:seen.update(m.visits)
 return dict(cases=len(cases),bodies=3,retail_words_visited=len(seen),float_model='finite single precision')
