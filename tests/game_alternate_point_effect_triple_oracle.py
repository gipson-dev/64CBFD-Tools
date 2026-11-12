import sys,struct,json,itertools
from dataclasses import dataclass
from pathlib import Path
from tools.experiments import game_alternate_point_effect_triple_match as match
root=match.ROOT;p=match.OUT
from tools.tests import test_game_point_interval_effect_match as g
from tools.pad_generated_object import parse_object
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
ENTRIES=(0x15147318,0x15147478,0x151475D8);NAMES=('func_15147318','func_15147478','func_151475D8');SELECT=0x15146890;EMIT=0x15141F78;EXTRA=0x15142180;PTR=(0x8008FD04,0x8008FD1C,0x8008FD30);SCALE=(0x800A573C,0x800A5744,0x800A574C);TAG=(0x800A5740,0x800A5748,0x800A5750);PROVIDERS=(0x151D97A8,0x151D99C8,0x151D9ADC);ALT=0x151D9A20;ACTOR=g.ACTOR;STACK=g.STACK;put,read=g.put,g.read
syms={v[1]:v[2][1] for v in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())}
def words(o,name):
 d,f,r=parse_object(o);at=f[name]['value'];n=f[name]['size'];refs={k-at:v for k,v in r.items() if at<=k<at+n};return tuple(bound_blob(d[at:at+n],refs,syms))

@dataclass(frozen=True)
class Case:
 kind:int=0;active:int=0x50000;mode:int=1;amount:int=115;value:int=0x3f800000;answer:int=1;mutation:int=0;phase:int=0;fcsr:int=0;actor:int=ACTOR;provider_return:int=0x12345678
def fixture(c):
 m={STACK+i:(i*17+165)&255 for i in range(-1024,1024)};m.update({c.actor+i:(i*13+91)&255 for i in range(0x340)})
 put(m,c.actor+0x1d4,c.active);put(m,c.actor+0x40,c.value);put(m,PTR[c.kind],PROVIDERS[c.kind]);put(m,SCALE[c.kind],0x3bfc0fc1);put(m,TAG[c.kind],0x3f360b61);return m
def select_effect(m,c,h):
 if c.mutation&1:put(m,c.actor+0x40,g.bits(27.5));put(m,SCALE[c.kind],g.bits(.5));put(m,TAG[c.kind],g.bits(2.));put(m,PTR[c.kind],ALT)
 if c.mutation&2:put(m,h+8,0xffffff85)
def provider_effect(m,c,h,p,r):
 if c.mutation&4:put(m,h+8,115);put(m,c.actor+0x40,g.bits(19.5));put(m,SCALE[c.kind],g.bits(.25));put(m,r+0x18,0x13579bdf);put(m,p,g.bits(4.25))
def emit_effect(m,c,h,p,r):
 if c.mutation&8:put(m,h+8,115);put(m,r+0x18,0x76543210);put(m,p,g.bits(-17.5))
def extra_effect(m,c,h,p,r):
 if c.mutation&16:put(m,PTR[c.kind],ALT);put(m,r+0x18,0x2468ace0);put(m,p+4,g.bits(12.5))
def public(m):return{a:b for a,b in m.items()if not STACK-1024<=a<STACK+1024}
def reference(initial,c):
 m=dict(initial);h=STACK+c.phase;pos=h-12;res=h-48;mode=c.mode&255;calls=[];obs=[]
 for off,val in ((0,c.actor),(4,c.mode),(8,c.amount)):put(m,h+off,val&0xffffffff)
 if not c.active:return public(m),calls,obs
 calls.append((SELECT,(pos,c.actor,res,mode)));g.fill(m,pos,res);select_effect(m,c,h)
 if not c.answer:return public(m),calls,obs
 def extra(slot):
  args=(slot,pos,read(m,res+0x18),g.bits(1.),g.bits(1.));calls.append((EXTRA,args));obs.append((EXTRA,g.packet(m,pos,12),read(m,res+0x18)));extra_effect(m,c,h,pos,res)
 if c.kind==0 and g.signed(read(m,h+8))>=115:extra(0)
 provider=read(m,PTR[c.kind]);calls.append((provider,()));provider_effect(m,c,h,pos,res)
 amount=read(m,h+8);scale=g.product(g.single(float(g.signed(amount))),read(m,SCALE[c.kind]));tag=g.converted(g.product(read(m,c.actor+0x40),read(m,TAG[c.kind])));args=(c.provider_return&255,res,scale,tag,pos,mode);calls.append((EMIT,args));obs.append((EMIT,g.packet(m,res,36),g.packet(m,pos,12)));emit_effect(m,c,h,pos,res)
 if c.kind!=0 and g.signed(read(m,h+8))>=115:extra((0,6,11)[c.kind])
 return public(m),calls,obs
class Oracle(g.Oracle):
 def __init__(self,code,c):
  self.cc=c;self.obs=[];g.Oracle.__init__(self,code,fixture(c),c,entry=ENTRIES[c.kind]);self.home=STACK+c.phase
 def record_call(self,t):
  if t in (*PROVIDERS,ALT):a=()
  else:
   counts={SELECT:4,EMIT:6,EXTRA:5};assert t in counts,hex(t);a=tuple(map(g.u32,self.arguments(counts[t])))
  self.calls.append((t,a))
  if t==EMIT:self.obs.append((EMIT,g.packet(self.memory,a[1],36),g.packet(self.memory,a[4],12)));self.assert_control()
  if t==EXTRA:self.obs.append((EXTRA,g.packet(self.memory,a[1],12),a[2]));self.assert_control()
 def hook(self,t):
  c=self.cc;a=self.calls[-1][1];h=self.home;pos=h-12;res=h-48;value=0x12345678
  if t==SELECT:g.fill(self.memory,a[0],a[2]);select_effect(self.memory,c,h);value=c.answer
  elif t in (*PROVIDERS,ALT):provider_effect(self.memory,c,h,pos,res);value=c.provider_return
  elif t==EMIT:emit_effect(self.memory,c,h,pos,res)
  elif t==EXTRA:extra_effect(self.memory,c,h,pos,res)
  else:raise AssertionError(hex(t))
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for r in (1,2,3,*range(4,16),24,25):self.r[r]=0xa5000000+r
  self.f[:20]=[0xa5000000+i for i in range(20)];self.r[2]=value&0xffffffff
def run(state):
 one,_=match.pad_both(state)
 raw=[state['raw_words'][n] for n in NAMES];retail=[state['retail_words'][n] for n in NAMES];padded=[words(one,n) for n in NAMES]
 assert retail==padded
 counts=[0,0,0];visits=[set(),set(),set()]
 cases=[]
 for kind,mode,active,answer,amount,phase in itertools.product(range(3),range(256),(0,0x50000),(0,1),(114,115),(0,8)):
  cases.append(Case(kind=kind,mode=0xabcd0000|mode,active=active,answer=answer,amount=amount,mutation=(0,1,4,8,16)[mode%5],phase=phase,value=g.VALUES[mode%len(g.VALUES)],fcsr=(0,3,0xa5a50003)[mode%3],provider_return=(0,255,0x12345678,0xffffffff)[mode%4]))
 for kind,mode,amount,mutation,phase in itertools.product(range(3),(0,1,2,255),(114,115),range(32),(0,8)):
  cases.append(Case(kind=kind,mode=mode,amount=amount,mutation=mutation,phase=phase))
 for c in cases:
  kind=c.kind;want,calls,obs=reference(fixture(c),c)
  for code in (raw[kind],retail[kind],padded[kind]):
   m=Oracle(code,c).run();m.assert_control();assert (public(m.memory),m.calls,m.obs)==(want,calls,obs),(c,code is raw[kind],m.calls,calls);assert m.r[29]==STACK+c.phase
   if code is retail[kind]:visits[kind].update(m.visits)
  counts[kind]+=1
 return dict(cases_per_target=counts,bodies=3,retail_words_visited=list(map(len,visits)),conversion='bounded FCSR model',helpers='modeled')
