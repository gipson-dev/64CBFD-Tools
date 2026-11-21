"""Ordered position math, finite trig providers, and the original scalar spring."""
from pathlib import Path
from dataclasses import dataclass,replace
from functools import lru_cache
import itertools,json,struct,sys
from tools.experiments import game_camera_position_151247c0_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.test_game_trig_match import operation as fp
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
ENTRY,SIZE,CAMERA,PRIMARY,PARTNER,ACTIVITY,OTHER=0x151247C0,756,0x30000,0x50000,0x51000,0x52000,0x53000
SPRING,FINAL,SIN,COS=0x150495B0,0x15125594,0x15047D60,0x15047C00
SYMS={'func_150495B0':SPRING,'func_15125594':FINAL,'sinf':SIN,'cosf':COS,'D_800A34FC':0x800A34FC,'D_800A3500':0x800A3500}
LUT=tuple(map(bits,(0.,-0.,.25,-.5,.75,-1.,1.25,2.)))
@dataclass(frozen=True)
class Case:
 phase:int=0;disabled:int=0;secondary:int=1;flags:int=0;state:int=0;counter:int=0;paired:int=0;pattern:int=0;offset:int=0;target:int=0;dt:int=0x3F800000;mutation:int=0;alias:int=0;profile:int=0
def trig(t,arg,c):return LUT[((arg>>20)^(arg>>8)^(3 if t==COS else 0)^c.profile)&7]
def fixture(c):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-1024,512)}
 for base,n in((CAMERA,0xA00),(PRIMARY,0x300),(PARTNER,0x300),(ACTIVITY,0xA0),(OTHER,0x300)):
  m.update({base+i:(i*29+0x35)&255 for i in range(n)})
 p=CAMERA+0x290 if c.alias==3 else PRIMARY;q=p if c.alias==1 else p+4 if c.alias==4 else PARTNER
 a=CAMERA+0x5D8 if c.alias==2 else ACTIVITY
 for base,j in((p,0),(q,1),(OTHER,2)):
  for k in range(3):put(m,base+0x14+4*k,bits((j*17+k*5-11)*(c.pattern+1)*.25))
 put(m,a+0x9C,c.flags);m[a+0x95]=c.state
 for at,v in((0x3D0,p),(0x248,q if c.paired else 0),(0x3D4,a if c.secondary else 0)):put(m,CAMERA+at,0 if c.disabled else v)
 for at,v in((0x2A4,bits(2.5)),(0x2A8,bits(-3.)),(0x2AC,bits(7.25)),(0x670,bits((0.,.125,1.,-1.)[c.pattern%4])),
  (0x674,bits(1.)),(0x678,bits((0.,.5,-.25,2.)[c.pattern%4])),(0x3B4,bits((0.,1.,8.,32.)[c.pattern%4])),
  (0x3B8,bits((0.,.25,1.,4.)[c.pattern%4])),(0x7B4,c.dt),(0x994,c.offset),(0x998,bits(.25)),(0x99C,c.target),(0x39C,bits((0.,1.5707964,3.1415927,-1.)[c.pattern%4]))):put(m,CAMERA+at,v)
 m[CAMERA+0x23C]=c.counter;put(m,CAMERA+0x244,c.paired,2);put(m,CAMERA+0x7F4,c.disabled,2)
 put(m,SYMS['D_800A34FC'],0x3FC90FDB);put(m,SYMS['D_800A3500'],0x3FC90FDB)
 return m
def public(m):return{a:b for a,b in m.items()if not STACK-1024<=a<STACK+512}
def spring(m,p,target,v,strength,damping,dt):
 difference=fp(target,read(m,p),'sub');direction=bits(-1. if floating(difference)<0. else 1.)
 difference=fp(difference,strength,'mul');velocity=read(m,v)
 acceleration=fp(fp(fp(difference,velocity,'sub'),damping,'mul'),dt,'mul')
 put(m,v,fp(velocity,acceleration,'add'));next_value=fp(fp(read(m,v),dt,'mul'),read(m,p),'add')
 next_direction=bits(-1. if floating(target)<floating(next_value)else 1.)
 if next_direction==direction:put(m,p,next_value)
 else:put(m,p,target);put(m,v,0)
def spring_effect(m,c,p):
 if not c.mutation:return
 if p==CAMERA+0x670:
  m[CAMERA+0x23C]=1 if c.mutation&1 else 0;put(m,CAMERA+0x244,1,2);put(m,CAMERA+0x3D0,OTHER);put(m,CAMERA+0x248,PARTNER);put(m,CAMERA+0x7B4,bits(.25))
 else:
  put(m,CAMERA+0x39C,bits(-2.5));put(m,SYMS['D_800A34FC'],bits(.5));put(m,SYMS['D_800A3500'],bits(-.25))
def finish_effect(m,c):put(m,CAMERA+0x37C,read(m,CAMERA+0x2BC)^0x80000000)
def reference(initial,c):
 m=dict(initial);calls=[]
 def smooth(p,target,v,s,d,dt):calls.append((SPRING,(p,target,v,s,d,dt)));spring(m,p,target,v,s,d,dt);spring_effect(m,c,p)
 if read(m,CAMERA+0x7F4,2):return public(m),calls
 a=read(m,CAMERA+0x3D4);active=(read(m,a+0x9C)|m[a+0x95])&255 if a else 0
 put(m,CAMERA+0x674,bits(.25 if active else 1.))
 if m[CAMERA+0x23C]:put(m,CAMERA+0x670,read(m,CAMERA+0x674));put(m,CAMERA+0x678,0)
 else:smooth(CAMERA+0x670,read(m,CAMERA+0x674),CAMERA+0x678,fp(read(m,CAMERA+0x3B4),bits(.25),'mul'),fp(read(m,CAMERA+0x3B8),bits(.25),'mul'),read(m,CAMERA+0x7B4))
 p=read(m,CAMERA+0x3D0);q=read(m,CAMERA+0x248)if read(m,CAMERA+0x244,2)else 0
 target=[fp(fp(read(m,p+0x14+4*j),read(m,q+0x14+4*j),'add'),bits(.5),'mul')if q else read(m,p+0x14+4*j)for j in range(3)]
 factor=read(m,CAMERA+0x670)
 for j in range(3):
  at=CAMERA+0x2A4+4*j;old=read(m,at);value=target[j]if m[CAMERA+0x23C]or j==1 else fp(old,fp(fp(target[j],old,'sub'),factor,'mul'),'add');put(m,at,value)
 if floating(read(m,CAMERA+0x994))!=0. or floating(read(m,CAMERA+0x99C))!=0.:
  if m[CAMERA+0x23C]:put(m,CAMERA+0x994,read(m,CAMERA+0x99C));put(m,CAMERA+0x998,0)
  else:smooth(CAMERA+0x994,read(m,CAMERA+0x99C),CAMERA+0x998,bits(4.),bits(6.),read(m,CAMERA+0x7B4))
  a=fp(read(m,CAMERA+0x39C),read(m,SYMS['D_800A34FC']),'sub');calls.append((SIN,(a,)));x=fp(trig(SIN,a,c),read(m,CAMERA+0x994),'mul')
  a=fp(read(m,CAMERA+0x39C),read(m,SYMS['D_800A3500']),'sub');calls.append((COS,(a,)));z=fp(trig(COS,a,c),read(m,CAMERA+0x994),'mul')
  put(m,CAMERA+0x2A4,fp(read(m,CAMERA+0x2A4),x,'add'));put(m,CAMERA+0x2AC,fp(read(m,CAMERA+0x2AC),z,'add'))
 put(m,CAMERA+0x2BC,read(m,CAMERA+0x2A4));put(m,CAMERA+0x2C4,read(m,CAMERA+0x2AC));calls.append((FINAL,(CAMERA,)));finish_effect(m,c)
 return public(m),calls
@lru_cache(maxsize=1)
def helper_code():
 raw=(root/'conker/conker.us.bin').read_bytes()[0x76A60:0x76B38];elf=(out/'baseline/conker/build/conker.us.elf').read_bytes();at=elf_slot_offset(elf,SPRING,216);assert elf[at:at+216]==raw
 return dict(zip(range(SPRING,SPRING+216,4),struct.unpack('>54I',raw)))
class Machine(FactoryOracle):
 def __init__(self,words,c,m,connected=False):
  self.c=c;super().__init__(words,m,c,entry=ENTRY,s=SYMS,arguments=(CAMERA,),connected=helper_code()if connected else None)
 def record_call(self,t):
  if t==SPRING:a=tuple(self.arguments(6))
  elif t==FINAL:a=tuple(self.arguments(1));assert a==(CAMERA,)
  else:assert t in(SIN,COS),hex(t);a=(self.f[12],)
  self.calls.append((t,a));self.events.append(('CALL',t,a))
 def hook(self,t):
  answer=None
  if t==SPRING:spring(self.memory,*self.calls[-1][1]);spring_effect(self.memory,self.c,self.calls[-1][1][0])
  elif t==FINAL:finish_effect(self.memory,self.c)
  else:answer=trig(t,self.calls[-1][1][0],self.c)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011
  if answer is not None:self.f[0]=answer
def programs():return[bound_blob(*payload(p,'func_151247C0'),SYMS)for p in(out/'image-qualification/retail.o',out/'qualified-source/candidate.o',out/'image-qualification/qualified-owner/game_14FF90.c.o')]
def state(m):return(m.memory,m.r,m.f,m.hi,m.lo,m.condition,m.trace,m.calls,m.current_pc,m.delay_of)
def corpus():
 for counter,paired,secondary,flags,pattern,offset,target,dt,mutation in itertools.product((0,1),(0,1),(0,1),(0,0x100,0x80000001),range(4),(0,bits(2.)),(0,bits(-1.)),(0,bits(1.)),(0,1,2)):
  yield Case(counter=counter,paired=paired,secondary=secondary,flags=flags,pattern=pattern,offset=offset,target=target,dt=dt,mutation=mutation,state=pattern&1,phase=(pattern&1)*8)
 for field in('state','counter'):
  for v in range(256):yield replace(Case(paired=1,offset=bits(-.25),target=bits(1.),flags=0x100,pattern=v%4),**{field:v})
 for alias,counter,paired,disabled in itertools.product(range(1,5),(0,255),(0,0x8000),(0,1,65535)):
  yield Case(alias=alias,counter=counter,paired=paired,disabled=disabled,offset=bits(.5),target=bits(-1.),pattern=2)
 for offset,target in itertools.product((0x80000000,bits(-2.),bits(1e-30)),(0x80000000,bits(3.))):yield Case(offset=offset,target=target,dt=bits(.125),pattern=1)
def compare(streams,c,connected=False):
 initial=fixture(c);expected=reference(initial,c);machines=[]
 for words in streams:
  m=Machine(words,c,dict(initial),connected).run();assert(public(m.memory),m.calls)==expected,(c,m.calls,expected[1]);machines.append(m)
 assert all(state(m)==state(machines[0])for m in machines[1:]),c
 return machines[0]
def run():
 streams=programs();assert streams[0]==streams[1]==streams[2];coverage=set();count=0
 for c in corpus():
  m=compare(streams,c);coverage.update((pc-ENTRY)//4 for pc in m.visits if ENTRY<=pc<ENTRY+SIZE);count+=1
 from tools.tests.game_camera_state_flags_151236d0_guest import static_reachable
 reachable=static_reachable(streams[0]);assert coverage==reachable,sorted(reachable-coverage)
 connected_cases=0;seen=set();code=helper_code()
 for counter,paired,pattern,offset,target,dt,activity in itertools.product((0,1),(0,1),range(4),(0,bits(-.5),bits(2.)),(0,bits(-1.),bits(2.)),(0,bits(.125),bits(1.)),(0,1)):
  c=Case(counter=counter,paired=paired,pattern=pattern,offset=offset,target=target,dt=dt,state=activity);m=compare(streams,c,True);seen.update(m.visits&code.keys());connected_cases+=1
 helper_words=[code[p]for p in sorted(code)];helper_reachable={SPRING+4*i for i in static_reachable(helper_words)}
 assert seen==helper_reachable,sorted(helper_reachable-seen)
 faults=0;examples=[Case(),Case(counter=1,paired=1,offset=bits(2.),target=bits(-1.)),Case(pattern=2,mutation=1,offset=bits(2.))]
 for c in examples:
  full=compare(streams,c)
  for cut in range(full.all_accesses):
   states=[]
   for words in streams:
    m=Machine(words,c,fixture(c));m.cut=cut
    try:m.run();raise AssertionError('missing access cut')
    except AccessBoundary:pass
    states.append(state(m))
   assert states[0]==states[1]==states[2];faults+=1
 r={'cases_per_stream':count,'streams':3,'covered_words':len(coverage),'static_unreachable_words':sorted(set(range(189))-reachable),
 'original_spring_cases_per_stream':connected_cases,'original_spring_words_covered':len(seen),'original_spring_unreachable_words':sorted((p-SPRING)//4 for p in set(code)-helper_reachable),'access_fault_prefixes':faults,
 'full_memory_private_bytes_registers_calls_and_ordered_accesses_equal':True,
 'limits':'Finite float32 model with pure finite trig and bounded finalization. Provider mutations and camera/actor overlap aliases are separate from actual spring execution; no FCSR/hardware claim.',
 'source_installed':packet.installed(),'matching_credit':0}
 (out/'guest-qualification.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
if __name__=='__main__':run()
