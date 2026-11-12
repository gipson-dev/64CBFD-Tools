import sys,struct,json,itertools
from dataclasses import dataclass
from pathlib import Path
from tools.experiments import game_actor_point_emit_150beacc_match as match
root=match.ROOT;p=match.OUT
from tools.tests import test_game_point_interval_effect_match as g
from tools.pad_generated_object import parse_object
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
ENTRY=0x150BEACC;SELECT=0x150BE9B0;EMIT=0x15141F78;EXTRA=0x15142180;K0,K1,K2,K3=0x800A00C0,0x800A00C4,0x800A00C8,0x800A00CC;ACTOR=g.ACTOR;STACK=g.STACK;put,read=g.put,g.read
syms={v[1]:v[2][1] for v in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())}
def words(o):
 d,f,r=parse_object(o);at=f['func_150BEACC']['value'];n=f['func_150BEACC']['size'];refs={k-at:v for k,v in r.items() if at<=k<at+n};return tuple(bound_blob(d[at:at+n],refs,syms))

@dataclass(frozen=True)
class Case:
 active:int=0x50000;mode:int=1;amount:int=85;value:int=0x3f800000;answer:int=1;mutation:int=0;phase:int=0;fcsr:int=0;actor:int=ACTOR
def fixture(c):
 m={STACK+i:(i*17+165)&255 for i in range(-1024,1024)};m.update({c.actor+i:(i*13+91)&255 for i in range(0x340)})
 put(m,c.actor+0x1d4,c.active);put(m,c.actor+0x40,c.value)
 for addr,v in ((K0,0x3c40c0c1),(K1,0x404b53f8),(K2,0x3f360b61),(K3,0x401be76d)):put(m,addr,v)
 return m
def result_fill(m,p,r):g.fill(m,p,r)
def pre_effect(m,c,h):
 if c.mutation&1:put(m,c.actor+0x40,g.bits(27.5));put(m,K0,g.bits(.5));put(m,K2,g.bits(2.))
 if c.mutation&2:put(m,h+8,0xffffff85)
 if c.mutation&4:put(m,c.actor+0x1d4,0)
def emit_effect(m,c,p,r):
 if c.mutation&8:put(m,r+0x18,0x76543210);put(m,p,g.bits(-17.5))
def public(m):return{a:b for a,b in m.items()if not STACK-1024<=a<STACK+1024}
def reference(initial,c):
 m=dict(initial);h=STACK+c.phase;pos=h-12;res=h-48;mode=c.mode&255;calls=[];observations=[]
 if c.active:
  calls.append((SELECT,(pos,c.actor,res,mode)));result_fill(m,pos,res);pre_effect(m,c,h)
  if c.answer:
   amount=read(m,h+8) if c.mutation&2 else c.amount&0xffffffff
   scale=g.product(g.product(g.single(float(g.signed(amount))),read(m,K0)),read(m,K1));tag=g.converted(g.product(read(m,c.actor+0x40),read(m,K2)))
   calls.append((EMIT,(11,res,scale,tag,pos,mode)));observations.append((g.packet(m,res,36),g.packet(m,pos,12)));emit_effect(m,c,pos,res)
   if g.signed(amount)>=76:calls.append((EXTRA,(2,pos,read(m,res+0x18),0x404ed917,read(m,K3))));observations.append((g.packet(m,pos,12),read(m,res+0x18)))
 return public(m),calls,observations
class Oracle(g.Oracle):
 def __init__(self,code,c):
  self.cc=c;self.obs=[];self.point=STACK+c.phase-12;self.result=STACK+c.phase-48
  g.Oracle.__init__(self,code,fixture(c),c,entry=ENTRY);self.home=STACK+c.phase
 def record_call(self,t):
  counts={SELECT:4,EMIT:6,EXTRA:5};assert t in counts,hex(t);a=tuple(map(g.u32,self.arguments(counts[t])));self.calls.append((t,a))
  if t==EMIT:self.obs.append((g.packet(self.memory,a[1],36),g.packet(self.memory,a[4],12)));self.assert_control()
  if t==EXTRA:self.obs.append((g.packet(self.memory,a[1],12),a[2]));self.assert_control()
 def hook(self,t):
  c=self.cc;a=self.calls[-1][1];val=0x12345678
  if t==SELECT:result_fill(self.memory,a[0],a[2]);pre_effect(self.memory,c,self.home);val=c.answer
  elif t==EMIT:emit_effect(self.memory,c,a[4],a[1])
  else:assert t==EXTRA
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for r in (1,2,3,*range(4,16),24,25):self.r[r]=0xa5000000+r
  self.f[:20]=[0xa5000000+i for i in range(20)];self.r[2]=val&0xffffffff
def run(state):
 one,_=match.pad_both(state)
 raw,retail,padded=state['raw_words'],state['retail_words'],words(one)
 assert retail==padded
 counts=0;seen=set()
 for mode,active,answer,amount,mutation,phase in itertools.product(range(256),(0,0x50000),(0,1),(75,76), (0,1,2,8),(0,8)):
  c=Case(mode=0xabcd0000|mode,active=active,answer=answer,amount=amount,mutation=mutation,phase=phase,value=g.VALUES[mode%len(g.VALUES)],fcsr=(0,3,0xa5a50003)[mode%3]);initial=fixture(c);want,calls,obs=reference(initial,c)
  for code in (raw,retail,padded):
   m=Oracle(code,c).run();m.assert_control();assert (public(m.memory),m.calls,m.obs)==(want,calls,obs),(c,code is raw,m.calls,calls);assert m.r[29]==STACK+phase
   if code is retail:seen.update(m.visits)
  counts+=1
 return dict(cases=counts,bodies=3,retail_words_visited=len(seen),conversion='bounded FCSR model')
