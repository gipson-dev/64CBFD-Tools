"""Bounded finite execution screen; excludes enabled traps and nonfinite inputs.

This is a private candidate discriminator, not an installation qualification.
It reuses the existing MIPS interpreter and exact finite Fraction arithmetic.
"""
from pathlib import Path
from dataclasses import dataclass
import itertools,json,math,struct,sys
sys.path.insert(0,str(Path.cwd()))
from tools.tests.game_payload_effect_factory_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_interpolated_particle_emitter_150d1204_guest import arithmetic,fp
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments import game_timed_phase_update_15108658_match as p
o=p.OUT;ENTRY=0x15108658;POINT=0x30000;SCRATCH=0x50000;RNG=0x150ada68
DELTA,EDGE,RATE=0x800be9a4,0x800a2460,0x800a2464
symbols=dict(func_150ADA68=RNG,D_800BE9A4=DELTA,D_800A2460=EDGE,D_800A2464=RATE)
bits,floating=fp.bits,fp.floating
@dataclass(frozen=True)
class Case:
 remaining:float=10.;total:float=20.;transition:float=2.;edge:float=1.;cooldown:float=0.;delta:float=0.;limit:float=.25;rng:float=.125;mutation:int=0;phase:int=0;fcsr:int=0
def fixture(c):
 m={STACK+c.phase+i:(i*17+165)&255 for i in range(-256,128)}
 for p,n in((POINT,188),(SCRATCH,16)):
  for i in range(-8,n+8):m[p+i]=(i*29+91)&255
 for i,v in enumerate((c.remaining,c.total,c.transition,c.edge,c.cooldown)):put(m,POINT+0xa8+4*i,bits(v))
 for p,v in((DELTA,c.delta),(EDGE,.25),(RATE,c.limit)):put(m,p,bits(v))
 return m
def public(m,c):return{a:v for a,v in m.items()if not STACK+c.phase-256<=a<STACK+c.phase+128}
def effect(m,c):
 if c.mutation:
  put(m,POINT+0xa8,bits(-91.));put(m,POINT+0xb8,bits(-17.));put(m,RATE,bits(.75));put(m,DELTA,bits(2.));m[SCRATCH]=0x7e
def reference(initial,c):
 m=dict(initial);fcsr=c.fcsr;calls=[];snapshots=[]
 def sub(a,b):
  nonlocal fcsr
  v,flags=arithmetic(a,b,1,fcsr&3);fcsr=(fcsr&~0x3f000)|flags;return v
 def lt(a,b):
  nonlocal fcsr
  assert math.isfinite(floating(a))and math.isfinite(floating(b))
  fcsr&=~0x3f000;return floating(a)<floating(b)
 def eq(a,b):
  nonlocal fcsr
  fcsr&=~0x3f000;return floating(a)==floating(b)
 current=read(m,POINT+0xa8);first=lt(current,read(m,POINT+0xb4));left=sub(read(m,POINT+0xac),current)
 if first or lt(left,read(m,POINT+0xb4)):put(m,POINT+0x1c,0)
 elif lt(read(m,POINT+0xa8),read(m,POINT+0xb0))or lt(left,read(m,POINT+0xb0)):put(m,POINT+0x1c,0x10000)
 else:put(m,POINT+0x1c,0x20000)
 current=read(m,POINT+0xb8)
 if not eq(0,current):
  edge=read(m,EDGE);first=lt(current,edge);left=sub(bits(11.),current)
  if first or lt(left,edge):put(m,POINT+0x1c,0);m[POINT+0x74]=255
  else:m[POINT+0x74]=3
  value=sub(read(m,POINT+0xb8),read(m,DELTA));put(m,POINT+0xb8,value)
  if lt(read(m,POINT+0xb8),0):put(m,POINT+0xb8,0);m[POINT+0x74]=255
 else:
  value=sub(read(m,POINT+0xa8),read(m,DELTA));put(m,POINT+0xa8,value)
  if lt(read(m,POINT+0xa8),0):return m,0,calls,snapshots,fcsr
  if read(m,POINT+0x1c)==0x20000:
   calls.append(RNG);snapshots.append((public(m,c),fcsr));effect(m,c);fcsr=c.fcsr&3
   if lt(bits(c.rng),read(m,RATE)):put(m,POINT+0xb8,bits(11.))
 return m,1,calls,snapshots,fcsr
class Machine(FactoryOracle):
 def __init__(self,words,c):
  self.c=c;super().__init__(words,fixture(c),c,entry=ENTRY,arguments=(POINT,SCRATCH));self.initial=dict(self.memory);self.fcsr=c.fcsr;self.fp_operations=[];self.observations=[]
 def execute(self,w):
  op,fmt,rt,fs,fd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
  if op==17 and fmt==16 and fn in(1,50,60):
   a,b=self.f[fs],self.f[rt];self.fp_operations.append((fn,a,b))
   assert math.isfinite(floating(a))and math.isfinite(floating(b)),(hex(w),a,b)
   if fn==1:self.f[fd],flags=arithmetic(a,b,1,self.fcsr&3);self.fcsr=(self.fcsr&~0x3f000)|flags
   else:self.condition=floating(a)==floating(b)if fn==50 else floating(a)<floating(b);self.fcsr&=~0x3f000
  else:super().execute(w)
 def record_call(self,t):
  assert t==RNG;self.calls.append(t);self.observations.append((public(self.memory,self.c),self.fcsr))
 def hook(self,t):
  assert t==RNG;effect(self.memory,self.c)
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for i in(1,2,3,*range(4,16),24,25):self.r[i]=0xa5000000+i
  self.f[:20]=[0xa5000000+i for i in range(20)];self.f[0]=bits(self.c.rng);self.r[2]=0xa5000002;self.hi,self.lo=0xa5000010,0xa5000011;self.fcsr=self.c.fcsr&3
def cases():
 rows=[Case(remaining=v,total=20.,cooldown=c,delta=d,rng=f,mutation=m,fcsr=rm,phase=8*(rm&1))for v,c,d,f,m,rm in itertools.product((-1.,0.,.5,1.5,2.,10.,18.5,19.5,21.),(0.,-0.,2**-30,.25,1.,10.875,11.,12.,-1.),(0.,.125),(0.,.25),(0,1),range(4))]
 return rows

from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
g=sys.modules[__name__]
def state(m):return m.memory,m.r,m.f,m.fcsr,m.condition,m.hi,m.lo,m.calls,m.observations,m.trace,m.fp_operations,m.current_pc,m.delay_of,m.all_accesses
def main():
 files=['normalized-target.o','qualified-owner/generic.o','qualified-owner/generated.o','original-target.o','selected-final/owner-candidate.o'];programs=[g.bound_blob(*g.payload(o/f,'func_15108658'),g.symbols)for f in files];assert all(ws==programs[0]for ws in programs[:4]);seen=set();rows=g.cases();prefixes=0
 for c in rows:
  models=[]
  for ws in programs:
   m=g.Machine(ws,c).run();wanted,answer,calls,obs,fcsr=g.reference(m.initial,c);assert(g.public(m.memory,c),m.r[2],m.calls,m.observations,m.fcsr)==(g.public(wanted,c),answer,calls,obs,fcsr);models.append(m)
  a=models[0];assert all(state(m)==state(a)for m in models[1:4]);raw=models[-1]
  assert(raw.memory,raw.r[2],raw.fcsr,raw.condition,raw.hi,raw.lo,raw.calls,raw.observations)==(a.memory,a.r[2],a.fcsr,a.condition,a.hi,a.lo,a.calls,a.observations)
  assert[x for x in raw.fp_operations if x[0]==1]==[x for x in a.fp_operations if x[0]==1];seen.update(a.visits)
 for c in(g.Case(),g.Case(mutation=1),g.Case(cooldown=2**-30),g.Case(cooldown=-1.),g.Case(cooldown=11.,delta=.125),g.Case(remaining=-1.),g.Case(remaining=1.5),g.Case(remaining=18.5,fcsr=3)):
  complete=g.Machine(programs[0],c).run()
  for cut in range(complete.all_accesses):
   models=[]
   for ws in programs[:4]:
    m=g.Machine(ws,c);m.cut=cut
    try:m.run();raise AssertionError('Missing access boundary')
    except AccessBoundary:models.append(m)
   assert all(state(m)==state(models[0])for m in models[1:]);prefixes+=1
 missing=[hex(i*4)for i in range(105)if g.ENTRY+i*4 not in seen];assert missing==['0x54','0x88','0x11c','0x14c']
 q=dict(cases_per_stream=len(rows),streams=5,retail_identical_streams=4,retail_executed_words=len(seen),retail_unreachable_duplicate_offsets=missing,access_fault_quads=prefixes,raw_public_private_memory_and_integer_return_and_FCSR_equal=True,raw_ordered_arithmetic_operators_operands_equal=True,raw_compare_interleaving_may_differ=True,raw_fault_prefix_and_scratch_register_equality_not_claimed=True,finite_traps_disabled_reference_only=True,source_installed=p.installed(),matching_credit=0)
 (o/'guest.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True)
 return q
if __name__=='__main__':main()
