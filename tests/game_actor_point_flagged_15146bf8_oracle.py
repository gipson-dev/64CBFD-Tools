"""Independent bounded guest model for the flagged actor-point effect."""
import itertools
from dataclasses import dataclass
from tools.experiments import game_actor_point_flagged_15146bf8_match as match
from tools.tests import test_game_point_interval_effect_match as g
from tools.pad_generated_object import parse_object
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
ENTRY=0x15146BF8;SELECT=0x15146890;EMIT=0x15141F78;EXTRA=0x15142180
K0,K1=0x800A5720,0x800A5724
ACTOR,OTHER,STACK=g.ACTOR,g.OTHER,g.STACK
put,read=g.put,g.read

def words(path):
 d,f,r=parse_object(path);at=f[match.NAME]['value'];n=f[match.NAME]['size'];refs={k-at:v for k,v in r.items() if at<=k<at+n}
 syms={v[1]:v[2][1] for v in symbol_rows((match.ROOT/'conker/build/conker.us.elf').read_bytes())}
 return tuple(bound_blob(d[at:at+n],refs,syms))

@dataclass(frozen=True)
class Case:
 active:int=0x50000;mode:int=1;amount:int=115;flag:int=0;value:int=0x3f800000;answer:int=1;mutation:int=0;phase:int=0;fcsr:int=0;actor:int=ACTOR

def fixture(c):
 m={STACK+i:(i*17+165)&255 for i in range(-1024,1024)}
 for a in(c.actor,OTHER):m.update({a+i:(i*13+91)&255 for i in range(0x340)})
 put(m,c.actor+0x1d4,c.active);put(m,c.actor+0x40,c.value);put(m,OTHER+0x40,g.bits(3.75));put(m,K0,0x3bfc0fc1);put(m,K1,0x3f360b61)
 return m

def select_effect(m,c,h):
 if c.mutation&1:put(m,c.actor+0x40,g.bits(27.5));put(m,K0,g.bits(.5));put(m,K1,g.bits(2.))
 if c.mutation&2:put(m,h+8,0xffffff85)
 if c.mutation&4:put(m,h+12,0x100 if c.flag&255 else 0x101)
 if c.mutation&8:put(m,h,OTHER)

def emit_effect(m,c,h,p,r):
 if c.mutation&16:put(m,h+8,115);put(m,r+0x18,0x76543210);put(m,p,g.bits(-17.5))

def public(m):return {a:b for a,b in m.items() if not STACK-1024<=a<STACK+1024}

def reference(initial,c,home=None):
 m=dict(initial);h=STACK+c.phase if home is None else home;p=h-12;r=h-48;mode=c.mode&255;calls=[];obs=[]
 for off,val in ((0,c.actor),(4,c.mode),(8,c.amount),(12,c.flag)):put(m,h+off,g.u32(val))
 if read(m,c.actor+0x1d4):
  calls.append((SELECT,(p,c.actor,r,mode)));g.fill(m,p,r);select_effect(m,c,h)
  if c.answer:
   slot=12 if read(m,h+15,1) else 11;amount=read(m,h+8);actor=read(m,h)
   scale=g.product(g.single(float(g.signed(amount))),read(m,K0));tag=g.converted(g.product(read(m,actor+0x40),read(m,K1)))
   calls.append((EMIT,(slot,r,scale,tag,p,mode)));obs.append((EMIT,g.packet(m,r,36),g.packet(m,p,12)));emit_effect(m,c,h,p,r)
   if g.signed(read(m,h+8))>=115:calls.append((EXTRA,(2,p,read(m,r+0x18),g.bits(1.),g.bits(1.))));obs.append((EXTRA,g.packet(m,p,12),read(m,r+0x18)))
 return public(m),calls,obs

class Oracle(g.Oracle):
 def __init__(self,code,c):
  self.cc=c;self.obs=[];g.Oracle.__init__(self,code,fixture(c),c,entry=ENTRY);self.home=STACK+c.phase;self.r[7]=g.u32(c.flag)
 def record_call(self,t):
  counts={SELECT:4,EMIT:6,EXTRA:5};assert t in counts,hex(t);a=tuple(map(g.u32,self.arguments(counts[t])));self.calls.append((t,a))
  if t==EMIT:self.obs.append((EMIT,g.packet(self.memory,a[1],36),g.packet(self.memory,a[4],12)));self.assert_control()
  if t==EXTRA:self.obs.append((EXTRA,g.packet(self.memory,a[1],12),a[2]));self.assert_control()
 def hook(self,t):
  c=self.cc;a=self.calls[-1][1];h=self.home;val=0x12345678
  if t==SELECT:g.fill(self.memory,a[0],a[2]);select_effect(self.memory,c,h);val=c.answer
  elif t==EMIT:emit_effect(self.memory,c,h,a[4],a[1])
  else:assert t==EXTRA
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.r[2]=g.u32(val)

def run(state):
 one,_=match.pad_both(state);raw,retail,padded=state['raw_words'],state['retail_words'],words(one);assert retail==padded
 cases=[]
 for mode,flag,active,answer,amount,phase in itertools.product(range(256),(0,1,0x100,0x101),(0,0x50000),(0,1),(114,115),(0,8)):
  cases.append(Case(mode=0xabcd0000|mode,flag=flag,active=active,answer=answer,amount=amount,phase=phase,mutation=(0,1,2,4,8,16)[mode%6],value=g.VALUES[mode%len(g.VALUES)],fcsr=(0,3,0xa5a50003)[mode%3]))
 for flag,mutation,phase in itertools.product(range(256),range(32),(0,8)):
  cases.append(Case(flag=0xabcd0000|flag,mutation=mutation,phase=phase))
 seen=set()
 for c in cases:
  want,calls,obs=reference(fixture(c),c)
  for code in (raw,retail,padded):
   m=Oracle(code,c).run();m.assert_control();assert (public(m.memory),m.calls,m.obs)==(want,calls,obs),(c,code is raw,m.calls,calls);assert m.r[29]==STACK+c.phase
   if code is retail:seen.update(m.visits)
 return dict(cases=len(cases),bodies=3,retail_words_visited=len(seen),conversion='bounded FCSR model')
