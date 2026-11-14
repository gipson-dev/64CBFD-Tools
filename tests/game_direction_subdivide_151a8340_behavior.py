from pathlib import Path
from dataclasses import dataclass,replace
import itertools,json,re,struct,subprocess
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_paired_float_approach_1505a250_oracle import floating,bits,rounded
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests import game_direction_update_151a7a90_behavior as parent
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
ENTRY,RANDOM=0x151a8340,0x150ada68
RECORD,BASE,ALT=0x30000,0x70030,0x71030
u32=lambda v:v&0xffffffff
signed16=lambda v:((v&65535)^32768)-32768
fb=lambda v:bits(rounded(v))
@dataclass(frozen=True)
class Case:
 first:int=0
 last:int=7
 amplitude:float=1.
 depth:int=4
 mutation:int=0
 phase:int=0
 seed:int=0
 record:int=RECORD

def arguments(c):return c.record,u32(c.first),u32(c.last),fb(c.amplitude),u32(c.depth)
def fixture(c):
 m={STACK+i:(i*17+c.seed*13+0xa5)&255 for i in range(-2048,2304)}
 m.update({c.record+i:(i*19+c.seed*7)&255 for i in range(256)})
 for base,shift in ((BASE,0),(ALT,1)):
  for i in range(-2,14):
   for j,v in enumerate((.25*i+shift,.5*i-shift,-.125*i,10.+i,20.+i,30.+i)):put(m,base+24*i+4*j,fb(v))
 put(m,c.record+100,BASE);return m
def public(m):return {a:v for a,v in m.items() if not STACK-2048<=a<STACK+2304}
def sample(c,n):return (.125,.75,.5,1.,0.,-.25)[(n+c.seed)%6]
def effect(m,c,n):
 if c.mutation&1:
  put(m,c.record+100,ALT if n&1 else BASE)
  p=BASE+24*signed16(c.first)
  for i,delta in enumerate((.125,-.25,.5)):put(m,p+4*i,fb(floating(read(m,p+4*i))+delta))
 if c.mutation&2:
  for base in (BASE,ALT):
   for i in range(-2,14):
    p=base+24*i
    for axis,delta in enumerate((.125,.25,-.125)):put(m,p+4*axis,fb(floating(read(m,p+4*axis))+delta))
def reference(initial,c):
 m=dict(initial);calls=[];observed=[];draws=0
 def rng():
  nonlocal draws
  calls.append((RANDOM,()));observed.append((RANDOM,read(m,c.record+100)));answer=fb(sample(c,draws));draws+=1;effect(m,c,draws);return answer
 def recurse(first,last,amplitude,depth):
  first,last,depth=map(signed16,(first,last,depth));iterations=0
  while last-first>=2 and depth>0:
   iterations+=1;assert iterations<=16
   middle=signed16(first+((last-first)>>1));base=read(m,c.record+100);left=base+first*24;right=base+last*24
   delta=tuple(fb(floating(read(m,right+4*i))-floating(read(m,left+4*i))) for i in range(3))
   a=rng();double=fb(floating(amplitude)+floating(amplitude));negative=amplitude^0x80000000
   def noisy(axis,draw):
    center=fb(floating(read(m,left+4*axis))+floating(fb(floating(delta[axis])*.5)));noise=fb(floating(fb(floating(draw)*floating(double)))+floating(negative));return fb(floating(noise)+floating(center))
   put(m,read(m,c.record+100)+middle*24,noisy(0,a));a=rng();put(m,read(m,c.record+100)+middle*24+4,noisy(1,a));put(m,read(m,c.record+100)+middle*24+8,fb(floating(read(m,left+8))+floating(fb(floating(delta[2])*.5))))
   depth=signed16(depth-1);calls.append((ENTRY,(c.record,u32(first),u32(middle),amplitude,u32(depth))));recurse(first,middle,amplitude,depth);first=middle
 recurse(c.first,c.last,fb(c.amplitude),c.depth);return m,calls,observed
class Oracle(FactoryOracle):
 def __init__(self,words,memory,c,entry=ENTRY,connected=None):
  self.observed=[];self.draws=0;super().__init__(words,memory,c,entry=entry,arguments=arguments(c),connected=connected);self.before_f=self.f[:]
 def execute(self,w):
  op,fmt,ft,fs,fd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
  if op==17 and fmt==16 and fn in (0,1,2,7):
   if fn==7:self.f[fd]=self.f[fs]^0x80000000
   else:
    a,b=floating(self.f[fs]),floating(self.f[ft]);self.f[fd]=fb(a+b if fn==0 else a-b if fn==1 else a*b)
   self.r[0]=0
  else:super().execute(w)
 def record_call(self,t):
  assert t in (ENTRY,RANDOM),hex(t);a=tuple(self.arguments(5 if t==ENTRY else 0));self.calls.append((t,a));self.events.append(('CALL',t,a))
  if t==RANDOM:self.observed.append((t,read(self.memory,self.case.record+100)))
 def hook(self,t):
  assert t==RANDOM;answer=fb(sample(self.case,self.draws));self.draws+=1;effect(self.memory,self.case,self.draws)
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=u32(0xa5000000+reg)
  self.f[:20]=[0xa5000000+i for i in range(20)];self.f[0]=answer;self.r[2]=0xa5000002;self.hi,self.lo=0xa5000010,0xa5000011
def cases():
 for first,last,depth,amplitude,mutation,phase in itertools.product((-2,0,3),(3,7,13),(-1,0,1,2,4),(0.,-0.,.5,-2.),(0,1,2),(0,8)):
  yield Case(first=first,last=last,depth=depth,amplitude=amplitude,mutation=mutation,phase=phase)
 for first,last,depth in ((0x12340001,0x87650007,0x34560003),(7,3,4),(0,0,32767),(0,1,32767),(0,2,32767),(0,2,0x12348000)):
  yield Case(first=first,last=last,depth=depth)
def load():
 r=Path.cwd();o=r/'conker/build/game-direction-subdivide-151a8340-screen';asm=(r/'conker/asm/1D4E00.s').read_text();a=asm.index('glabel func_151A8340\n');z=asm.index('endlabel func_151A8340',a)+len('endlabel func_151A8340');(o/'retail.s').write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+asm[a:z]+'\n.size func_151A8340,.-func_151A8340\n')
 subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(o/'retail.o'),str(o/'retail.s')],cwd=r/'conker',capture_output=True,check=True)
 sy={a[1]:a[2][1] for a in symbol_rows((r/'conker/build/conker.us.elf').read_bytes())}
 return [bound_blob(*payload(o/f,'func_151A8340'),sy) for f in ('retail.o','selected.o','guarded.o')]
def state(m):return parent.machine_state(m)
class CoupledOracle(parent.Oracle):
 def __init__(self,words,memory,c,hc,connected):
  self.helper_case=hc;self.draws=0;self.helper_rng=False;super().__init__(words,memory,c,connected=connected)
 def execute(self,w):
  if w>>26==17 and w>>21&31==16 and w&63==7:self.f[w>>6&31]=self.f[w>>11&31]^0x80000000;self.r[0]=0
  else:super().execute(w)
 def record_call(self,t):
  self.helper_rng=t==RANDOM and ENTRY<=self.r[31]-8<ENTRY+544
  if self.helper_rng:
   self.calls.append((t,()));self.events.append(('CALL',t,()));self.observed.append((t,read(self.memory,self.case.record+100)))
  else:super().record_call(t)
 def hook(self,t):
  if not(self.helper_rng and t==RANDOM):return super().hook(t)
  answer=fb(sample(self.helper_case,self.draws));self.draws+=1
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=u32(0xa5000000+reg)
  self.f[:20]=[0xa5000000+i for i in range(20)];self.f[0]=answer;self.r[2]=0xa5000002;self.hi,self.lo=0xa5000010,0xa5000011
def run():
 programs=load();assert programs[0]==programs[2];count=0;seen=[set() for p in programs]
 for c in cases():
  initial=fixture(c);expected,calls,obs=reference(initial,c)
  states=[]
  for i,p in enumerate(programs):
   m=Oracle(p,initial,c);m.run();assert (public(m.memory),m.calls,m.observed)==(public(expected),calls,obs),(c,i)
   assert m.r[29]==m.before[29] and all(m.r[j]==m.before[j] for j in (*range(16,24),28,30,31)) and m.f[20:]==m.before_f[20:]
   states.append(state(m))
   seen[i].update(m.visits)
  assert states[0]==states[2]
  count+=1
 assert [len(s) for s in seen]==[136,135,136]
 aliases=0
 for kind,phase,amplitude in itertools.product((0,1),(0,8),(0.,1.)):
  c=Case(first=0,last=2,depth=2,phase=phase,amplitude=amplitude,record=STACK+phase+0x180 if kind==0 else RECORD);initial=fixture(c)
  if kind:
   base=STACK+phase-8
   for j in range(3):
    for axis,v in enumerate((.25*j,.5*j,-.125*j)):put(initial,base+24*j+4*axis,fb(v))
   put(initial,c.record+100,base)
  states=[]
  for p in (programs[0],programs[2]):
   m=Oracle(p,initial,c);m.run();states.append(state(m))
   if kind==0:
    expected,calls,obs=reference(initial,c);assert bytes(m.memory[c.record+i] for i in range(256))==bytes(expected[c.record+i] for i in range(256)) and m.calls==calls and m.observed==obs
  assert states[0]==states[1];aliases+=1
 prefixes=0
 for c in (Case(last=1),Case(last=2,depth=0),Case(last=2,mutation=1),Case(last=5,depth=2,mutation=2)):
  initial=fixture(c);whole=Oracle(programs[0],initial,c);whole.run()
  for cut in range(whole.all_accesses):
   states=[]
   for p in (programs[0],programs[2]):
    m=Oracle(p,initial,c);m.cut=cut
    try:m.run()
    except AccessBoundary:pass
    else:raise AssertionError('missing fired boundary')
    states.append(state(m))
   assert states[0]==states[1];prefixes+=1
 _,parents,_,crosscode=parent.load();coupled=0
 for n,amplitude,phase,real_cross in itertools.product((0,1,2,3,5),(0.,-0.,.5,-2.),(0,8),(False,True)):
  c=parent.Case(count=n,timer=-.25,phase=phase,real_cross=real_cross);hc=Case(last=n-1,depth=100,phase=phase,amplitude=amplitude);initial=parent.fixture(c);put(initial,c.record+32,fb(amplitude));before=dict(initial);put(before,c.record+104,fb(c.timer-c.timestep))
  expected,calls,obs=reference(before,hc);calls=[(ENTRY,(c.record,0,u32(signed16(n-1)),fb(amplitude),100))]+calls
  obs.append((RANDOM,read(expected,c.record+104)));calls.append((RANDOM,()));put(expected,c.record+104,fb(c.sample*c.range+c.minimum));saved_time=read(expected,parent.TIME);put(expected,parent.TIME,fb(0.));expected,cc,co=parent.reference(expected,c);put(expected,parent.TIME,saved_time);calls+=cc;obs+=co
  states=[]
  for i,p in enumerate(programs):
   code=dict(zip(range(ENTRY,ENTRY+4*len(p),4),p))
   if real_cross:code.update(crosscode)
   m=CoupledOracle(parents[0],initial,c,hc,code);m.run();assert (public(m.memory),m.calls,m.observed)==(public(expected),calls,obs),(n,amplitude,phase,real_cross,i);states.append(state(m))
  assert states[0]==states[2];coupled+=1
 report=dict(cases=count,words=[len(p) for p in programs],observed=[len(s) for s in seen],guest_alias_cases=aliases,access_prefixes=prefixes,coupled_parent_cases=coupled,actual_parent_words=183,actual_cross_words=29,helpers_modeled=True)
 o=Path.cwd()/'conker/build/game-direction-subdivide-151a8340-screen';(o/'behavior.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':run()
