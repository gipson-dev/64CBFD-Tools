"""Bounded finite IEEE arithmetic, ordered RNG, packet snapshots and access faults."""
from pathlib import Path
from dataclasses import dataclass,replace
from functools import lru_cache
import itertools,json,struct,sys
from tools.experiments import game_interpolated_particle_emitter_150d1204_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests import game_paired_actor_initializer_151951e0_guest as fp
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
ENTRY=0x150D1204;FRNG=0x150ADA68;RNG=0x150ADA20;EMIT=0x151DB5D0
EMITTER=0x50000;OTHER=0x52000;VECTOR=0x30000;OUTPUT=0x70000;SIZE=0x1D8
GLOBALS=(0x800A0898,0x800A089C,0x800A08A0,0x800A08A4)
bits,floating=fp.bits,fp.floating;u32=lambda n:n&0xFFFFFFFF
def arithmetic(a,b,fn,rm=0):
 result,flags=fp.fp_result(a,b,fn,rm)
 x,y=floating(a),floating(b)
 exact=x+y if fn==0 else x-y if fn==1 else x*y
 if exact==0.0:
  if fn==2:sign=(a^b)&0x80000000
  else:
   effective=b^(0x80000000 if fn==1 else 0)
   sign=(a&0x80000000)if(a&0x7FFFFFFF)==(effective&0x7FFFFFFF)==0 and(a^effective)&0x80000000==0 else(0x80000000 if rm==3 else 0)
  return sign,0
 return result,flags
@dataclass(frozen=True)
class Case:
 vectors:tuple=tuple(bits(v)for v in(1.,-2.,3.,8.,5.,-9.,.5,1.25,-.75,3.,-4.,2.))
 fraction:int=bits(.25)
 coefficient:int=bits(2.)
 constants:tuple=tuple(bits(v)for v in(.5,1.25,4.,-2.))
 floats:tuple=(bits(.125),bits(.75))
 integers:tuple=(0xFFFFFFFF,0x80000000)
 kind:int=0xAB
 context:int=0xCD
 alias:int=0
 mode:int=0
 phase:int=0
 fcsr:int=0
 caller:bool=False
 rng_flags:tuple=(0,0)

def pointers(c):
 if c.caller:
  home=STACK+c.phase
  return tuple(home+i for i in(0xD4,0xC8,0xF8,0xEC))
 if c.alias==1:return(VECTOR,)*4
 if c.alias==2:return(VECTOR,VECTOR,VECTOR+64,VECTOR+64)
 if c.alias==3:return(EMITTER+0x6C,VECTOR+32,VECTOR+64,VECTOR+96)
 return tuple(VECTOR+32*i for i in range(4))
def fixture(c):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-1024,2048)}
 for base,n in((VECTOR-16,160),(EMITTER-16,SIZE+32),(OTHER-16,SIZE+32),(OUTPUT-16,64)):
  m.update({base+i:(i*19+0xA5)&255 for i in range(n)})
 for p in(EMITTER,OTHER):
  put(m,p+0x74,c.coefficient);m[p+0xC]=c.kind;m[p+1]=c.context
 for i,p in enumerate(pointers(c)):
  for j in range(3):put(m,p+4*j,c.vectors[3*i+j])
 if c.alias==3:put(m,EMITTER+0x74,c.coefficient)
 for p,v in zip(GLOBALS,c.constants):put(m,p,v)
 return m
def public(m):return{a:v for a,v in m.items()if not STACK-1024<=a<STACK+2048}
def snapshot(m,c):return(tuple(read(m,p+4*j)for p in pointers(c)for j in range(3)),
 tuple(read(m,p)for p in GLOBALS),bytes(m[EMITTER+i]for i in range(SIZE)),bytes(m[OTHER+i]for i in range(SIZE)))
def effect(m,c,target,ordinal,home):
 if target==FRNG:
  if c.mode&1 and ordinal==1:
   for p in pointers(c):
    for j in range(3):put(m,p+4*j,bits(40.+j))
   put(m,EMITTER+0x74,bits(17.))
  if c.mode&2 and ordinal==2:
   for p,v in zip(GLOBALS,(2.,3.,5.,7.)):put(m,p,bits(v))
   m[EMITTER+0xC]^=0x55;m[EMITTER+1]^=0xAA
  return c.floats[ordinal-1]
 if target==RNG:
  if c.mode&4:
   put(m,GLOBALS[2],bits(8.+ordinal));m[EMITTER+0xC]=(c.kind+ordinal)&255
  if c.mode&8 and ordinal==2:
   put(m,home+16,bits(99.));put(m,home+20,OTHER)
   m[OTHER+0xC]=0xFE;m[OTHER+1]=0x81
  return c.integers[ordinal-1]
 assert target==EMIT
 put(m,OUTPUT,0x13579BDF);return OUTPUT

def reference(initial,c,connected=False):
 m=dict(initial);home=STACK+c.phase;fcsr=c.fcsr;calls=[];observations=[];counts={}
 def calc(a,b,fn):
  nonlocal fcsr
  value,flags=arithmetic(a,b,fn,fcsr&3);fcsr=(fcsr&~0x3F000)|flags;return value
 vectors=[[read(m,p+4*j)for j in range(3)]for p in pointers(c)]
 first,second,step1,step2=vectors
 position=[calc(a,calc(b,c.fraction,2),0)for a,b in zip(first,step1)]
 other=[calc(a,calc(b,c.fraction,2),0)for a,b in zip(second,step2)]
 velocity=[calc(calc(a,b,1),read(m,EMITTER+0x74),2)for a,b in zip(other,position)]
 def call(t,args):
  nonlocal fcsr
  counts[t]=counts.get(t,0)+1;calls.append((t,tuple(map(u32,args))));observations.append((snapshot(m,c),tuple(position),tuple(velocity),fcsr))
  result=effect(m,c,t,counts[t],home)
  if connected and t==FRNG:fcsr=(fcsr&~0x3F000)|c.rng_flags[counts[t]-1]
  return result
 firstRandom=call(FRNG,());secondRandom=call(FRNG,());firstBits=call(RNG,());secondBits=call(RNG,())
 size=calc(calc(firstRandom,bits(61.),2),bits(60.),0)
 spread=calc(calc(secondRandom,read(m,GLOBALS[2]),2),read(m,GLOBALS[3]),0)
 emitter=OTHER if c.mode&8 else EMITTER
 args=(0,home-12,home-36,size,read(m,GLOBALS[0]),read(m,GLOBALS[1]),spread,
       (firstBits&15)+35,secondBits%156+100,30,8,0,m[emitter+0xC],m[emitter+1])
 call(EMIT,args)
 return m,calls,observations,fcsr

class Oracle(fp.Oracle):
 def __init__(self,words,c,entry=ENTRY,connected=None,memory=None,arguments=None):
  self.c=c;home=STACK+c.phase
  args=(*pointers(c),c.fraction,EMITTER)if arguments is None else arguments
  FactoryOracle.__init__(self,words,fixture(c)if memory is None else memory,c,entry=entry,arguments=args,connected=connected)
  self.initial=dict(self.memory);self.before_f=self.f[:];self.fcsr=c.fcsr;self.counts={};self.observations=[]
 def execute(self,w):
  op,fmt,rt,fs,fd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
  if op==17 and fmt==16 and fn in(0,1,2):
   self.f[fd],flags=arithmetic(self.f[fs],self.f[rt],fn,self.fcsr&3);self.fcsr=(self.fcsr&~0x3F000)|flags;self.r[0]=0
  else:super().execute(w)
 def record_call(self,t):
  assert t in(FRNG,RNG,EMIT,ENTRY),hex(t)
  args=tuple(map(u32,self.arguments(14 if t==EMIT else 6 if t==ENTRY else 0)))
  self.calls.append((t,args));self.events.append(('CALL',t,args));self.counts[t]=self.counts.get(t,0)+1
  home=STACK+self.c.phase
  packet=tuple(read(self.memory,home-12+4*i)for i in range(3)),tuple(read(self.memory,home-36+4*i)for i in range(3))
  self.observations.append((snapshot(self.memory,self.c),*packet,self.fcsr))
 def hook(self,t):
  value=effect(self.memory,self.c,t,self.counts[t],STACK+self.c.phase)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011
  self.r[2]=value
  if t==FRNG:self.f[0]=value

@lru_cache(maxsize=1)
def streams():
 ws=json.loads((out/'program.json').read_text());rom=(root/'conker/conker.us.bin').read_bytes()
 truth=list(struct.unpack_from('>102I',rom,0xFE6B4));assert ws==truth;return ws,truth
def state(m):return(m.memory,m.r,m.f,m.fcsr,m.hi,m.lo,m.calls,m.observations,m.trace,m.current_pc,m.delay_of,m.condition)
def check(ws,c):
 m=Oracle(ws,c).run();expected,calls,observations,fcsr=reference(m.initial,c)
 assert m.calls==calls,(c,'calls',m.calls,calls)
 assert public(m.memory)==public(expected),(c,'memory')
 # At the first four calls the final FCSR cause can differ because independent
 # packet operations are scheduled across components. Exact/inexact sticky
 # flags and the final parameter arithmetic are independently checked below.
 for actual,wanted in zip(m.observations,observations):
  assert actual[:3]==wanted[:3],(c,'packet/boundary')
  assert actual[3]&0x7F==wanted[3]&0x7F,(c,'sticky flags')
 assert m.fcsr==fcsr,(c,'final bounded FCSR',m.fcsr,fcsr)
 assert m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:]
 return m

def main():
 cases=[Case(kind=i,context=255-i)for i in range(256)]
 cases += [Case(fraction=bits(f),coefficient=bits(k),alias=a,mode=mode,phase=phase,fcsr=rm)
           for f,k,a,mode,phase,rm in itertools.product((0.,1.,-.5,.1),(0.,1.25,-2.),range(4),(0,7,15),(0,8),range(4))]
 cases += [Case(integers=(a,b))for a,b in itertools.product((0,1,15,16,155,156,0x7FFFFFFF,0x80000000,0xFFFFFFFF),repeat=2)]
 visits=set()
 for c in cases:
  a,b=[check(ws,c)for ws in streams()];assert state(a)==state(b);visits.update(a.visits)
 faults=0
 for c in(Case(),Case(alias=1,mode=7,phase=8),Case(alias=3,mode=15)):
  full=check(streams()[0],c)
  for cut in range(full.all_accesses):
   states=[]
   for ws in streams():
    m=Oracle(ws,c);m.cut=cut
    try:m.run();raise AssertionError('missing access cut')
    except AccessBoundary:pass
    states.append(state(m))
   assert states[0]==states[1];faults+=1
 missed=[i for i in range(102)if ENTRY+4*i not in visits];assert not missed,missed
 r=dict(cases_per_stream=len(cases),streams=2,target_executed_words=102,access_fault_pairs=faults,
        all_256_identity_bytes=True,all_four_rounding_modes=True,signed_zero_preserved=True,finite_bounded_IEEE_model=True,
        incoming_home_mutation_guest_only=True,emitter_input_alias_guest_only=True,
        RNG_and_emission_internals_modeled=True,source_installed=packet.installed(),matching_credit=0)
 (out/'guest.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
if __name__=='__main__':main()
