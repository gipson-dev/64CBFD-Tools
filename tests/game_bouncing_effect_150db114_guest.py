"""Finite ordered FP reference, complete instruction states and access faults."""
from pathlib import Path
from dataclasses import dataclass
import itertools,json,sys
sys.path.insert(0,str(Path.cwd()))
from tools.tests.game_payload_effect_factory_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_interpolated_particle_emitter_150d1204_guest import arithmetic,fp
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments import game_bouncing_effect_150db114_match as target_packet
o=target_packet.OUT;ENTRY=0x150DB114;DT=0x800BE9A4;POOL=0x800A0BE4;OBJECT=0x30000
bits,floating=fp.bits,fp.floating;OFFSETS=(0x110,0x114,0x118,0x34,0x38,0x3C,0x124,0x128,0x12C,0x130,0x11C,0x120,0x134)
@dataclass(frozen=True)
class Case:
 y:int=bits(1.)
 z:int=bits(1.)
 vy:int=bits(.5)
 vz:int=bits(-.5)
 damping:int=bits(.875)
 dt:int=bits(.25)
 alpha:int=128
 fade:int=1
 alias:int=0
 rm:int=0
 phase:int=0
 object:int=OBJECT
def symbols(c):
 dt=c.object+(0x34 if c.alias==1 else 0x110)if c.alias else DT
 return dict(D_800BE9A4=dt,D_800A0BE4=POOL,D_800A0BE8=POOL+4,D_800A0BEC=POOL+8,**{'.rodata':POOL})
def fixture(c):
 m={STACK+c.phase+i:(i*17+0xa5)&255 for i in range(-128,512)};m.update({c.object+i:(i*29+0x5a)&255 for i in range(-32,352)})
 values=(bits(1.125),bits(-2.5),bits(3.75),bits(12.),bits(-34.),bits(56.),c.y,c.z,c.vy,c.vz,bits(2.),bits(.125),c.damping)
 for off,v in zip(OFFSETS,values):put(m,c.object+off,v)
 m[c.object+0x5C]=c.alpha;m[c.object+0x138]=c.fade
 put(m,symbols(c)['D_800BE9A4'],c.dt)
 for i,v in enumerate((bits(1.2),bits(.8),bits(.8))):put(m,POOL+4*i,v)
 return m
def reference(initial,c,initial_fcsr=None):
 m=dict(initial);p=c.object;csr=c.rm if initial_fcsr is None else initial_fcsr;ops=[]
 def calc(a,b,fn):
  nonlocal csr
  ops.append((fn,a,b,csr));v,flags=arithmetic(a,b,fn,csr&3);csr=(csr&~0x3f000)|flags;return v
 def less(a,b):
  nonlocal csr
  ops.append((60,a,b,csr));flag=floating(a)<floating(b);csr=(csr&~(0x800000|0x3f000))|(0x800000 if flag else 0);return flag
 dt=symbols(c)['D_800BE9A4'];upper=bits(1.2);lower=bits(.8);damping=read(m,p+0x134);alpha=m[p+0x5C]
 velocity=[calc(read(m,p+x),damping,2)for x in(0x110,0x114,0x118)]
 for off,v in zip((0x110,0x114,0x118),velocity):put(m,p+off,v)
 for pos,vel in zip((0x34,0x38,0x3C),(0x110,0x114,0x118)):put(m,p+pos,calc(read(m,p+pos),calc(read(m,p+vel),read(m,dt),2),0))
 for pos,vel in((0x124,0x12C),(0x128,0x130)):
  put(m,p+pos,calc(read(m,p+pos),calc(read(m,p+vel),read(m,dt),2),0));v=read(m,p+pos)
  if less(upper,v):put(m,p+pos,upper);put(m,p+vel,read(m,p+vel)^0x80000000)
  elif less(v,lower):put(m,p+pos,lower);put(m,p+vel,read(m,p+vel)^0x80000000)
 put(m,p+0x11C,calc(read(m,p+0x11C),calc(read(m,p+0x120),read(m,dt),2),0))
 for pos,stretch in((0x2C,0x124),(0x30,0x128)):put(m,p+pos,calc(read(m,p+0x11C),read(m,p+stretch),2))
 alpha-=m[p+0x138];m[p+0x5C]=max(alpha,0);return m,ops,csr,int(alpha>=0)
class Machine(FactoryOracle):
 def __init__(self,words,c,memory=None,entry=None,arguments=None,connected=None):
  self.c=c;super().__init__(words,fixture(c)if memory is None else memory,c,entry=ENTRY if entry is None else entry,arguments=(c.object,)if arguments is None else arguments,s=symbols(c),connected=connected);self.initial=dict(self.memory);self.fcsr=c.rm;self.before_f=self.f[:];self.fp_operations=[]
 def execute(self,w):
  if w>>26==17 and w>>21&31==16 and w&63==7:self.f[w>>6&31]=self.f[w>>11&31]^0x80000000
  elif w>>26==17 and w>>21&31==16 and w&63 in(0,2,60):
   rt,fs,fd,fn=w>>16&31,w>>11&31,w>>6&31,w&63;a,b=self.f[fs],self.f[rt];self.fp_operations.append((fn,a,b,self.fcsr))
   if fn==60:self.condition=floating(a)<floating(b);self.fcsr=(self.fcsr&~(0x800000|0x3f000))|(0x800000 if self.condition else 0)
   else:self.f[fd],flags=arithmetic(a,b,fn,self.fcsr&3);self.fcsr=(self.fcsr&~0x3f000)|flags
  else:super().execute(w)
 def record_call(self,t):raise AssertionError(('leaf call',hex(t)))
 def hook(self,t):raise AssertionError(('leaf call',hex(t)))
def observable(m):return m.memory,m.fp_operations,m.fcsr,m.r[2]
def state(m):return m.memory,m.r,m.f,m.fcsr,m.hi,m.lo,m.calls,m.fp_operations,m.trace,m.current_pc,m.delay_of,m.condition
def check(words,c):
 m=Machine(words,c).run();want=reference(m.initial,c);assert observable(m)==want,dict(case=str(c),components=[a==b for a,b in zip(observable(m),want)],got=m.fp_operations,want=want[1]);assert all(m.r[i]==m.before[i]for i in(*range(16,24),28,29,30,31))and m.f[20:]==m.before_f[20:];return m
def cases():
 bounds=(bits(.5),bits(.8)-1,bits(.8),bits(1.),bits(1.2),bits(1.2)+1,bits(2.))
 rows=[Case(y=y,z=z,vy=0,vz=0,alpha=a,fade=f,rm=rm)for y,z,(a,f),rm in itertools.product(bounds,bounds,((0,0),(0,1),(127,128),(128,128),(255,1),(255,255)),range(4))]
 rows.extend(Case(y=bits(.8),z=bits(1.2),vy=v,vz=v^0x80000000,dt=d,damping=k,rm=rm,alias=alias,object=STACK+64 if st else OBJECT)for v,d,k,rm,alias,st in itertools.product((0,0x80000000,1,bits(.125),bits(-.125)),(bits(0),bits(.25),bits(-.5)),(bits(0),bits(.875),bits(1.)),range(4),range(3),(0,1)))
 return rows
def main():
 files=['original-target.o','selected-owner.o','normalized-target.o','qualified-owner/generic.o','qualified-owner/generated.o'];cache={};seen=set();rows=cases()
 for c in rows:
  key=tuple(sorted(symbols(c).items()))
  if key not in cache:cache[key]=[bound_blob(*payload(o/f,'func_150DB114'),symbols(c))for f in files]
  streams=cache[key];assert all(w==streams[0]for w in streams);models=[check(w,c)for w in streams];assert all(state(m)==state(models[0])for m in models[1:]);seen.update(models[0].visits)
 prefixes=0
 for c in(Case(y=bits(2),z=bits(2),alpha=0),Case(y=bits(.5),z=bits(.5)),Case(alias=1),Case(alias=2,object=STACK+64)):
  streams=[bound_blob(*payload(o/f,'func_150DB114'),symbols(c))for f in files];full=Machine(streams[0],c).run()
  for cut in range(full.all_accesses):
   models=[]
   for w in streams:
    m=Machine(w,c);m.cut=cut
    try:m.run();raise AssertionError('missing access fault')
    except AccessBoundary:models.append(m)
   assert all(state(m)==state(models[0])for m in models[1:]);prefixes+=1
 missing=sorted(set(range(ENTRY,ENTRY+452,4))-seen)
 q=dict(cases_per_stream=len(rows),streams=5,executed_words=len(seen),unreachable_words=[hex(x)for x in missing],fault_prefix_quintuples=prefixes,all_raw_and_padded_full_private_states_equal=True,finite_FP_model_not_hardware=True,all_four_rounding_modes=True,guest_DT_aliases_and_stack_adjacent_owner=True,alpha_unsigned_byte_subtraction_and_zero_boundary=True,readonly_pool_contiguous_and_immutable=True,source_installed=target_packet.installed(),matching_credit=0);(o/'guest.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
