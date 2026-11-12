"""Private finite-input guest screen for the script command handler."""
import sys,struct,itertools,json,math
from dataclasses import dataclass
from pathlib import Path
from tools.experiments import game_script_15079fbc_match as match
root=match.ROOT;p=match.OUT
from tools.pad_generated_object import parse_object
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests import test_game_point_interval_effect_match as g
STACK=g.STACK;put,read=g.put,g.read
ENTRY=0x15079fbc;LOOKUP=0x1507bb28;APPLY=0x15075f40;PLAYER=0x800cc2d0;CURRENT=0x800d154c;CMD=0x800d1890;FACTOR=0x8009a1e4;ACTOR=0x30000;OTHER=0x40000;META=0x50000;SCRIPT=0x60040
syms={v[1]:v[2][1] for v in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())}
def words(path):
 d,f,r=parse_object(path);at=f['func_15079FBC']['value'];n=f['func_15079FBC']['size'];refs={k-at:v for k,v in r.items() if at<=k<at+n};return tuple(bound_blob(d[at:at+n],refs,syms))
@dataclass(frozen=True)
class Case:
 actor:int=ACTOR;mode:int=0;amount:int=0;phase:int=0;fcsr:int=0;active:int=1;value:int=g.bits(12.5);factor:int=g.bits(.5);chased:int=0;mutation:int=0;cmd:int=7

def fixture(c):
 m={STACK+i:(i*17+165)&255 for i in range(-1024,1024)}
 for a,n in ((PLAYER,0x32c),(ACTOR,0x32c),(OTHER,0x32c),(META,0x100),(SCRIPT-32,128)):m.update({a+i:(i*13+91)&255 for i in range(n)})
 put(m,CURRENT,c.actor);put(m,PLAYER+0x65,c.active,1);put(m,PLAYER+0x44,c.value);put(m,PLAYER+0x31c,META);put(m,META+0x4c,0x91ab,2);put(m,META+0x4a,c.chased,1);put(m,FACTOR,c.factor)
 for i,v in enumerate((13,c.cmd,0x19,0xff)):put(m,CMD+i,v,1)
 return m

def public(m):return {a:b for a,b in m.items() if not STACK-1024<=a<STACK+1024}
def lookup_effect(m,c):
 if c.mutation&1:put(m,CURRENT,OTHER)
def apply_effect(m,c):
 if c.mutation&2:put(m,CURRENT,OTHER);put(m,OTHER+0xf4,0x34560001)
def reference(initial,c):
 m=dict(initial);calls=[];active=read(m,PLAYER+0x65,1);value=g.floating(read(m,PLAYER+0x44))
 if not active or value<5.:
  actor=read(m,CURRENT);put(m,actor+0x232,read(m,CMD+1,1),1);actor=read(m,CURRENT);calls.append((LOOKUP,(0,read(m,actor+0x232,1))));lookup_effect(m,c);actor=read(m,CURRENT);put(m,actor+0x218,SCRIPT);actor=read(m,CURRENT);put(m,actor+0x218,g.u32(read(m,actor+0x218)-5))
 else:
  meta=read(m,PLAYER+0x31c);actor=read(m,CURRENT);put(m,actor+0x78,read(m,meta+0x4c,2),2);meta=read(m,PLAYER+0x31c)
  f=read(m,PLAYER+0x44);f=f if read(m,meta+0x4a,1) else g.product(f,read(m,FACTOR));v=math.trunc(g.floating(f));speed=((v&0xffff)^0x8000)-0x8000
  if speed<17:put(m,CMD+3,(read(m,CMD+3,1)+1)&255,1);put(m,CMD,8,1)
  put(m,CMD+2,speed&255,1);calls.append((APPLY,()));apply_effect(m,c);actor=read(m,CURRENT);put(m,actor+0xf4,read(m,actor+0xf4)|0x40)
 return public(m),calls

class Oracle(g.Oracle):
 def __init__(self,code,c):self.cc=c;g.Oracle.__init__(self,code,fixture(c),c,entry=ENTRY)
 def execute(self,w):
  if w>>26==17 and (w>>21&31)==16 and (w&63)==13:
   fs=w>>11&31;fd=w>>6&31;value=g.floating(self.f[fs]);assert math.isfinite(value) and -(2**31)<=value<2**31;self.f[fd]=g.u32(math.trunc(value));self.r[0]=0
  else:super().execute(w)
 def record_call(self,t):
  assert t in (LOOKUP,APPLY),hex(t);a=tuple(map(g.u32,self.arguments(2 if t==LOOKUP else 0)));self.calls.append((t,a))
 def hook(self,t):
  c=self.cc;value=SCRIPT
  if t==LOOKUP:lookup_effect(self.memory,c)
  elif t==APPLY:apply_effect(self.memory,c)
  else:raise AssertionError(hex(t))
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.r[2]=g.u32(value)
def run(state):
 _,one=match.pad_both(state);raw,retail,padded=state['raw_words'],state['retail_words'],words(one);assert raw==retail==padded
 cases=[]
 for actor,active,value,factor,chased,mutation,phase in itertools.product((ACTOR,PLAYER),(0,1),(4.,5.,16.,16.75,17.,20.,255.,32767.),(.5,1.,.7),(0,1,0xff),range(4),(0,8)):
  cases.append(Case(actor=actor,active=active,value=g.bits(value),factor=g.bits(factor),chased=chased,mutation=mutation,phase=phase,cmd=(int(value)*7)&255))
 seen=set()
 for c in cases:
  want,calls=reference(fixture(c),c)
  for code in (raw,retail,padded):
   m=Oracle(code,c).run();assert (public(m.memory),m.calls)==(want,calls),(c,m.calls,calls);assert m.r[29]==STACK+c.phase
   if code is retail:seen.update(m.visits)
 result=dict(cases=len(cases),bodies=3,retail_words_visited=len(seen),bounded_finite_values=True,lookups_and_apply='modeled')
 return result


def fault_prefixes(state):
 _,padded=match.pad_both(state);bodies=(state['retail_words'],state['raw_words'],words(padded));count=0
 for c in (Case(active=0),Case(active=1,value=g.bits(4.)),Case(active=1,value=g.bits(5.),chased=0,mutation=2),Case(actor=PLAYER,active=1,value=g.bits(20.),chased=1),Case(active=0,mutation=1),Case(actor=PLAYER,active=1,value=g.bits(16.75),chased=0,mutation=2)):
  full=Oracle(bodies[0],c).run()
  for cut in range(full.all_accesses):
   states=[]
   for code in bodies:
    m=Oracle(code,c);m.cut=cut
    try:m.run();raise AssertionError(('missing access boundary',cut,c))
    except g.faults.AccessBoundary:pass
    states.append((m.trace,m.calls,public(m.memory),tuple(m.r),tuple(m.f),m.current_pc,m.delay_of))
   assert states[0]==states[1]==states[2],(c,cut);count+=1
 return dict(prefixes=count,cases=6,bodies=3,scope='modeled guest access boundary')
