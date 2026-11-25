"""Independent descriptor-byte, provider-order and finite-IEEE guest qualification."""
from pathlib import Path
from dataclasses import dataclass
from functools import lru_cache
import itertools,json,struct,sys
sys.path.insert(0,str(Path.cwd()))
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_interpolated_particle_emitter_150d1204_guest import arithmetic,fp
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments import game_random_particle_150b5e34_match as p
r,o=p.ROOT,p.OUT;ENTRY=0x150b5e34;RNG=0x150ada20;FRNG=0x150ada68;FACTORY=0x15130280;POINT,ALT,MARK,OUTPUT=0x30000,0x31000,0x35000,0x50000
bits=fp.bits;u32=lambda n:n&0xffffffff;HOLES=(*range(0x5c,0x60),*range(0x66,0x70))
@dataclass(frozen=True)
class Case:
 rng:tuple=(0xffffffff,1,0)
 sample:int=bits(.3)
 mode:int=255
 extra:int=0x87654321
 seed:int=0
 phase:int=0
 mutation:int=0
 fcsr:int=0
 ghost_homes:bool=False
 outcome:int=1
 coords:tuple=(bits(1.25),bits(-2.5),bits(3.75))
 point:int=POINT
def home(c):return STACK+c.phase
def packet(c):return home(c)-112
def arguments(c):return c.point,c.mode,u32(c.extra)
def data(m,a,n):return bytes(m[a+i]for i in range(n))
def public(m,c):return{a:v for a,v in m.items()if not home(c)-2048<=a<home(c)+1024}
def fixture(c,raw=False):
 m={home(c)+i:(i*17+c.seed*13+0xa5)&255 for i in range(-2048,1024)}
 for p,n in[(POINT,12),(ALT,12),(MARK,16),(OUTPUT,192)]:m.update({p+i:(i*29+c.seed*11+0x5a)&255 for i in range(n)})
 for p in(POINT,ALT):
  for i,v in enumerate(c.coords):put(m,p+4*i,v)
 put(m,MARK,0)
 if raw:
  a=home(c)-152+0x20;b=a+4;x=data(m,a,4);y=data(m,b,4)
  for i in range(4):m[a+i]=y[i];m[b+i]=x[i]
 return m
def provider_csr(c,epoch):return(c.fcsr&0x800003)|((epoch&31)<<2)
def effect(m,c,t,ordinal,args):
 put(m,MARK,read(m,MARK)+1)
 if c.mutation&1:
  for p in(POINT,ALT):
   for i in range(3):put(m,p+4*i,bits(float(ordinal*10+i+.25)))
 if c.ghost_homes:
  if ordinal==1:put(m,home(c),ALT)
  if ordinal in(2,3,4):put(m,home(c)+4,0xabcd0000+ordinal*0x11);put(m,home(c)+8,0xfedcba00+ordinal)
 if t==FACTORY:
  if c.mutation&2:
   for i in range(112):m[args[0]+i]=(i*7+c.seed*11+0x31)&255
  return OUTPUT if c.outcome else 0
 return c.sample if t==FRNG else c.rng[0 if ordinal==1 else ordinal-2]
def observation(m,c,t,args,fcsr):return(public(m,c),data(m,args[0],112)if t==FACTORY else b'',data(m,home(c),12),fcsr)
def reference(initial,c):
 m=dict(initial);d=packet(c);calls=[];obs=[];fcsr=c.fcsr
 for i,v in enumerate(arguments(c)):put(m,home(c)+4*i,v)
 def call(t,args=()):
  nonlocal fcsr
  args=tuple(map(u32,args));calls.append((t,args));obs.append(observation(m,c,t,args,fcsr));value=effect(m,c,t,len(calls),args);fcsr=provider_csr(c,len(calls));return value
 def calc(a,b,fn):
  nonlocal fcsr
  v,flags=arithmetic(a,b,fn,fcsr&3);fcsr=(fcsr&~0x3f000)|flags;return v
 m[d+0x1d]=43;put(m,d+8,0x4403,2);put(m,d,0x200005);put(m,d+4,0x20000)
 first=call(RNG);put(m,d+0xa,first%7+4,2);put(m,d+0xc,0);put(m,d+0x10,0)
 for i in range(0x14,0x1d):m[d+i]=255
 sample=call(FRNG);extent=calc(calc(sample,bits(500.),2),bits(500.),0);put(m,d+0x2c,extent);put(m,d+0x28,extent)
 position=read(m,home(c))
 for i in range(3):put(m,d+0x30+4*i,read(m,position+4*i))
 for at,v in[(0x1e,3),(0x20,85),(0x22,1)]:put(m,d+at,v,2)
 for at in range(0x3c,0x58,4):put(m,d+at,0)
 put(m,d+0x24,bits(1.));flag=(call(RNG)&1)*0x40;second=(call(RNG)&1)*0x80
 put(m,d+0x58,0xc201|flag|second)
 for at,v in[(0x60,6),(0x61,6),(0x62,255),(0x63,255),(0x64,255),(0x65,4)]:m[d+at]=v
 value=call(FACTORY,(d,1,0,0,m[home(c)+7],read(m,home(c)+8)))
 return m,calls,obs,fcsr,value
class Machine(FactoryOracle):
 def __init__(self,words,c,entry=ENTRY,raw=False,memory=None,args=None,connected=None):
  self.c=c;self.raw=raw;self.fcsr=c.fcsr;self.observations=[];self.mapped_frames=[];self.provider_count=0
  super().__init__(words,fixture(c,raw)if memory is None else memory,c,entry=entry,arguments=arguments(c)if args is None else args,connected=connected);self.initial=dict(self.memory);self.before_f=self.f[:]
 def execute(self,w):
  op,fmt,rt,fs,fd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
  if op==17 and fmt==16 and fn in(0,1,2):self.f[fd],flags=arithmetic(self.f[fs],self.f[rt],fn,self.fcsr&3);self.fcsr=(self.fcsr&~0x3f000)|flags
  else:super().execute(w)
  self.r[0]=0
 def frame(self):
  base=home(self.c)-152
  return bytes(self.memory[base+(i+4 if i<0x24 else i-4)if self.raw and 0x20<=i<0x28 else base+i]for i in range(152))
 def record_call(self,t):
  assert t in(RNG,FRNG,FACTORY),hex(t);args=tuple(map(u32,self.arguments(6 if t==FACTORY else 0)));self.calls.append((t,args));self.events.append(('CALL',t,args));self.observations.append(observation(self.memory,self.c,t,args,self.fcsr));self.mapped_frames.append(self.frame());self.provider_count+=1
 def hook(self,t):
  value=effect(self.memory,self.c,t,self.provider_count,self.calls[-1][1])
  for i in range(6 if t==FACTORY else 4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=u32(value);self.fcsr=provider_csr(self.c,self.provider_count)
  if t==FRNG:self.f[0]=value
def symbols():return dict(func_150ADA20=RNG,func_150ADA68=FRNG,func_15130280=FACTORY)
@lru_cache(maxsize=1)
def streams():
 rows=[bound_blob(*payload(o/f,'func_150B5E34'),symbols())for f in['normalized-target.o','qualified-owner/generic.o','qualified-owner/generated.o','original-target.o']]
 assert all(x==rows[0]for x in rows)and rows[0]==list(struct.unpack_from('>115I',(r/'conker/conker.us.bin').read_bytes(),0xe32e4));return rows
def raw_program():return bound_blob(*payload(o/'selected-final/owner-candidate.o','func_150B5E34'),symbols())
def cases():
 values=(0,1,6,7,8,0x7fffffff,0x80000000,0xffffffff)
 rows=[Case(mode=i,extra=u32(i*0x87654321),rng=(values[i%8],i&1,(i>>1)&1),mutation=i%4,phase=(i&1)*8,fcsr=i%4,seed=i&15,outcome=i&1)for i in range(256)]
 rows +=[Case(rng=(v,p&1,(p>>1)&1),mutation=m,fcsr=rm)for v,p,m,rm in itertools.product(values,range(4),(0,3),range(4))]
 rows +=[Case(extra=v,phase=phase,fcsr=rm,outcome=result)for v,phase,rm,result in itertools.product((0,0x80000000,0xffffffff),(0,8),range(4),(0,1))]
 rows +=[Case(ghost_homes=True,mutation=i%4,phase=(i&1)*8,seed=i)for i in range(16)]
 rows +=[Case(coords=(v,0x80000000,1),fcsr=rm)for v,rm in itertools.product((0x7f7fffff,0xff7fffff,0x00800000,0x80800000,0x7fc12345,0x7f800000),range(4))]
 rows +=[Case(sample=bits(v),fcsr=rm,mutation=m)for v,rm,m in itertools.product((.1,.3,-.0,-1.),range(4),(0,3))]
 return rows
def check(words,c,raw=False,entry=None):
 m=Machine(words,c,ENTRY if entry is None else entry,raw).run();expected,calls,obs,fcsr,value=reference(m.initial,c)
 assert m.calls==calls,(c,'calls',m.calls,calls);assert m.observations==obs,(c,'boundary observations');assert public(m.memory,c)==public(expected,c)and data(m.memory,packet(c),112)==data(expected,packet(c),112),(c,'memory')
 assert m.fcsr==fcsr and m.r[2]==value and m.r[29]==home(c)and m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:]
 return m
def state(m):return(m.memory,m.r,m.f,m.fcsr,m.hi,m.lo,m.calls,m.observations,m.trace,m.current_pc,m.delay_of,m.condition)
def main():
 programs=streams();raw=raw_program();visited=set();count=prefixes=0
 for c in cases():
  models=[check(ws,c)for ws in programs];assert all(state(m)==state(models[0])for m in models[1:]);a=models[0];b=check(raw,c,True)
  assert(a.calls,a.observations,a.mapped_frames,a.frame(),a.r,a.f,a.fcsr)==(b.calls,b.observations,b.mapped_frames,b.frame(),b.r,b.f,b.fcsr),(c,'mapped raw');visited.update(a.visits);count+=1
 from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
 for c in[Case(),Case(mutation=3,phase=8),Case(mutation=3,ghost_homes=True),Case(rng=(0,0,0),outcome=0)]:
  full=Machine(programs[0],c).run()
  for cut in range(full.all_accesses):
   models=[]
   for ws in programs:
    m=Machine(ws,c);m.cut=cut
    try:m.run();raise AssertionError('Missing access cut')
    except AccessBoundary:models.append(m)
   assert all(state(m)==state(models[0])for m in models[1:]);prefixes+=1
 assert visited==set(range(ENTRY,ENTRY+460,4))
 q=dict(cases_per_stream=count,streams=5,retail_equal_streams=4,all115_words_visited=True,access_fault_quads=prefixes,full112_byte_packet=True,initialized_packet_bytes=98,unspecified_packet_bytes=14,all256_mode_bytes=True,integer_modulus_boundaries_and_all_parity_pairs=True,all_four_rounding_modes_and_finite_inexact_cases=True,bitcopy_extremes_include_nonfinite_positions=True,guest_FP_samples_finite_ordinary_range=True,public_and_packet_mutations=True,guest_only_incoming_home_redirects=True,raw_private_spill_bytes=4,raw_private_initial_bytes_bijected=True,full_mapped_frame_at_calls_and_return_equal=True,allocation_pointer_or_null_result_equal=True,raw_physical_private_bytes_and_fault_order_not_claimed=True,source_installed=p.installed(),matching_credit=0)
 (o/'guest.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
