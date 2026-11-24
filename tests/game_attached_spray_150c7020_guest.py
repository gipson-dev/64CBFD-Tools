"""Independent sparse-packet model with ordered providers and live retained fields."""
from dataclasses import dataclass,replace
from functools import lru_cache
import itertools,json,struct
from tools.experiments import game_attached_spray_150c7020_match as p
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
ENTRY=0x150c7020;RNG=0x150ada20;PREPARE=0x1516962c;SUBMIT=0x15134dac;CONSTANT=0x800a0490
OWNER=0x30000;ALT=0x32000;MARK=0x50000
GAPS=(1,2,3,9,10,11,0x25,0x2c,0x2d,0x31,0x32,0x33,0x3a,0x3b)
DEFINED=tuple(i for i in range(60)if i not in GAPS)
u32=lambda n:n&0xffffffff
half=lambda n:((n&65535)^32768)-32768
@dataclass(frozen=True)
class Case:
 owner:int=OWNER
 lifetime:int=0
 tag:int=0xab
 coefficient:int=0x3ef1a9fd
 rng:tuple=(0xffffffff,0x80000000,0,65)
 mode:int=0
 phase:int=0
 seed:int=0
 ignored2:int=0xfedc00ff
 ignored3:int=0x89abcdef
def args(c):return tuple(map(u32,(c.owner,c.lifetime,c.ignored2,c.ignored3)))
def data(m,a,n):return bytes(m[a+i]for i in range(n))
def fixture(c):
 home=STACK+c.phase;m={home+i:(i*17+c.seed*13+0xa5)&255 for i in range(-2048,2048)}
 for base,n in((OWNER-16,128),(ALT-16,128),(MARK-16,48)):m.update({base+i:(i*29+c.seed*11+0x5a)&255 for i in range(n)})
 for a in(OWNER,ALT):m[a+0x3b]=c.tag
 if c.owner:m[c.owner+0x3b]=c.tag;put(m,CONSTANT,c.coefficient)
 return m
def public(m,c):return{a:v for a,v in m.items()if not STACK+c.phase-2048<=a<STACK+c.phase+2048}
def effect(m,c,t,ordinal,home):
 packet=home-60;put(m,MARK,(t+ordinal)&0xffffffff)
 if t==PREPARE:
  if c.mode&1:m[c.owner+0x3b]^=0x55;put(m,CONSTANT,c.coefficient^0x80000000)
  if c.mode&8:put(m,home,ALT);put(m,home+4,0xffff8001)
  return 0x12345678
 if t==RNG:
  if c.mode&2:
   m[OWNER+0x3b]^=ordinal;put(m,CONSTANT,0x7fc12345)
   m[packet+0x2f]=(m[packet+0x2f]+ordinal)&255
  return c.rng[ordinal-1]
 assert t==SUBMIT
 if ordinal==1 and c.mode&4:
  for i in range(60):m[packet+i]=(i*7+c.seed+0x39)&255
 return (0,0x60000)[ordinal&1]
def reference(initial,c):
 m=dict(initial);home=STACK+c.phase;packet=home-60;calls=[];observations=[];counts={}
 for i,v in enumerate(args(c)):put(m,home+4*i,v)
 if not c.owner:return m,calls,observations
 def call(t,a=()):
  counts[t]=counts.get(t,0)+1;calls.append((t,tuple(map(u32,a))))
  if t==SUBMIT:observations.append(data(m,packet,60))
  return effect(m,c,t,counts[t],home)
 call(PREPARE,(0x29,c.owner,0x12));owner=read(m,home);life=half(read(m,home+4))
 m[packet]=m[owner+0x3b];put(m,packet+4,owner)
 for at,v,n in ((8,13,1),(0x24,0,1),(0x2e,255,1),(0x2f,1,1),(0x30,255,1),(0x38,2,1),(0x39,255,1),(0xc,0x40000000,4),(0x10,0,4),(0x14,0x42080000,4),(0x18,0xc1700000,4),(0x1c,0,4),(0x20,0x42080000,4)):
  put(m,packet+at,v,n)
 put(m,packet+0x34,read(m,CONSTANT));put(m,packet+0x2a,life if life else 300,2)
 if life:m[packet+0x24]=2
 put(m,packet+0x26,call(RNG)%66+35,2);put(m,packet+0x28,call(RNG)%26+25,2);call(SUBMIT,(packet,0))
 for at,v,n in ((8,12,1),(0xc,0xc0000000,4),(0x10,0,4),(0x14,0x42080000,4),(0x18,0x41700000,4),(0x1c,0,4),(0x20,0x42080000,4)):
  put(m,packet+at,v,n)
 put(m,packet+0x26,call(RNG)%66+35,2);put(m,packet+0x28,call(RNG)%26+25,2);call(SUBMIT,(packet,0));return m,calls,observations
class Oracle(FactoryOracle):
 def __init__(self,words,c,entry=None,memory=None,arguments=None,connected=None):
  self.c=c;self.observations=[];self.counts={};super().__init__(words,fixture(c)if memory is None else memory,c,entry=ENTRY if entry is None else entry,arguments=args(c)if arguments is None else arguments,connected=connected);self.initial=dict(self.memory)
 def get(self,a,n):
  if getattr(self,'recording',False)and self.own_instruction:assert all(a+i in self.memory for i in range(n)),('Unmapped',hex(a),n)
  return super().get(a,n)
 def record_call(self,t):
  counts={PREPARE:3,RNG:0,SUBMIT:2,ENTRY:4};assert t in counts,hex(t);a=tuple(map(u32,self.arguments(counts[t])));self.calls.append((t,a));self.events.append(('CALL',t,a));self.counts[t]=self.counts.get(t,0)+1
  if t==SUBMIT:self.observations.append(data(self.memory,a[0],60))
 def hook(self,t):
  value=effect(self.memory,self.c,t,self.counts[t],STACK+self.c.phase)
  for i in range(4):self.put(self.r[29]+i*4,0xb5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=u32(value)
@lru_cache(maxsize=1)
def streams():
 s={'D_800A0490':CONSTANT,'func_150ADA20':RNG,'func_1516962C':PREPARE,'func_15134DAC':SUBMIT};rows=[]
 for f in[p.OUT/'selected-final/owner-candidate.o',p.OUT/'qualified-owner/generic.o',p.OUT/'qualified-owner/generated.o',p.OUT/'original-target.o']:
  rows.append(bound_blob(*payload(f,p.FUNCTION),s))
 assert all(v==rows[0]for v in rows);assert rows[0]==list(struct.unpack_from('>104I',(p.ROOT/'conker/conker.us.bin').read_bytes(),0xf44d0));return rows
def state(m):return(m.memory,m.r,m.f,m.hi,m.lo,m.calls,m.observations,m.trace,m.current_pc,m.delay_of,m.condition)
def cases():
 rows=[Case(owner=0,phase=phase)for phase in(0,8)]
 rows += [Case(tag=i,lifetime=(0,1,-1,-32768,32767)[i%5],mode=i%8,phase=(i%2)*8,seed=i%16,coefficient=(0,0x80000000,1,0x7f800000,0xff800000,0x7fc12345,0x7fa12345,0x3ef1a9fd)[i%8])for i in range(256)]
 rows += [Case(lifetime=life,mode=mode,phase=phase,seed=mode,ignored2=0x80000000+mode,ignored3=0xffffffff-mode)for life,mode,phase in itertools.product((0,1,-1,-32768,32767,0xabcd0000,0x12348000),range(16),(0,8))]
 rows += [Case(rng=(i,i,i,i),seed=i%16,mode=i%8,lifetime=i-33)for i in range(66)]
 rows += [Case(rng=(v,v,v,v),lifetime=v,mode=15)for v in(0x7fffffff,0x80000000,0xfffffffe,0xffffffff)]
 return rows
def check(words,c,entry=None):
 m=Oracle(words,c,entry=entry).run();wanted,calls,observations=reference(m.initial,c);assert(public(m.memory,c),m.calls,m.observations)==(public(wanted,c),calls,observations),(c,m.calls,calls);assert m.r[29]==STACK+c.phase;return m
def main():
 programs=streams();count=0;visits=set();faults=0;tags=set()
 for c in cases():
  models=[check(ws,c)for ws in programs];assert all(state(m)==state(models[0])for m in models);visits.update(models[0].visits);count+=1
  if models[0].observations:tags.add(models[0].observations[0][0])
 for c in[Case(owner=0),Case(),Case(lifetime=-32768,mode=15,phase=8)]:
  full=Oracle(programs[0],c).run()
  for cut in range(full.all_accesses):
   models=[]
   for ws in programs:
    m=Oracle(ws,c);m.cut=cut
    try:m.run();raise AssertionError('Missing access cut')
    except AccessBoundary:models.append(m)
   assert all(state(m)==state(models[0])for m in models);faults+=1
 assert visits==set(range(ENTRY,ENTRY+416,4)),set(range(ENTRY,ENTRY+416,4))-visits
 q=dict(cases_per_stream=count,streams=4,executed_words=len(visits),access_fault_quads=faults,full60byte_packets=True,seeded_padding_bytes=len(GAPS),all31_or_more_random_residues=True,ordered_provider_calls=True,mutable_packet_retained=True,guest_home_mutations=True,source_installed=p.installed(),matching_credit=0);(p.OUT/'guest.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
