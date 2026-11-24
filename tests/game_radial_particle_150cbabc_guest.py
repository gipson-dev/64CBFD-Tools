"""Fifteen-word radial ABI, sparse packets, payload copy and closed stack map."""
from dataclasses import dataclass,replace
from functools import lru_cache
import itertools,json,struct
from tools.experiments import game_radial_particle_150cbabc_match as p
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.game_interpolated_particle_emitter_150d1204_guest import arithmetic,fp
ENTRY,RNG,FRNG,DIRECTION,SUBMIT,COPY=0x150cbabc,0x150ada20,0x150ada68,0x15143794,0x15130374,0x10022ec0
OUTPUT,MARK=0x90000,0x70000
CONSTANTS=(0x800a0624,0x800a0628,0x800a062c,0x800a0630)
VALUES=(1137213440, 1008981770, 1065520988, 1064715683)
bits,floating=fp.bits,fp.floating;u32=lambda v:v&0xffffffff
half=lambda v:((v&65535)^32768)-32768
KNOWN=tuple([*range(0x3c),*range(0x48,0x5c),*range(0x60,0x64)])
BEFORE_DIRECTION=tuple([*range(0x1e),*range(0x28,0x3c),0x60,0x61])
@dataclass(frozen=True)
class Case:
 coords:tuple=(bits(1.25),bits(-2.5),bits(3.75))
 angle:int=0xabcd80fe
 slot:int=0x123400e1
 rng:tuple=(0xffffffff,0x80000000,0xffffffff,1,0)
 samples:tuple=(bits(.125),bits(.75))
 constants:tuple=VALUES
 unused:tuple=(0xa1234567,0xffff8001,0x7fc12345,0x3f123456,0xffc54321,0x987654ff,0x40000000,0x87654321,0x3f400000,0xabcdef01)
 outcome:int=1
 mode:int=0
 phase:int=0
 fcsr:int=0
 seed:int=0
 home_mutations:bool=False
def args(c):
 a,b,ox,oy,oz,start,radius,style,extra,context=c.unused
 return tuple(map(u32,(a,b,*c.coords,ox,oy,oz,c.angle,start,radius,style,extra,context,c.slot)))
def packet(c,raw=False):return STACK+c.phase-(112 if raw else 116)
def damping(c,raw=False):return STACK+c.phase-(120 if raw else 124)
def rngslot(c,raw=False):return STACK+c.phase-(128 if raw else 132)
def data(m,a,n):return bytes(m[a+i]for i in range(n))
def public(m,c):return{a:v for a,v in m.items()if not STACK+c.phase-2048<=a<STACK+c.phase+4096}
def fixture(c,raw=False):
 home=STACK+c.phase;m={home+i:(i*17+c.seed*13+0xa5)&255 for i in range(-2048,4096)}
 for base,n in((OUTPUT-16,0xcc),(MARK,32)):m.update({base+i:(i*29+c.seed*11+0x5a)&255 for i in range(n)})
 for i,v in enumerate(args(c)):put(m,home+4*i,v)
 for a,v in zip(CONSTANTS,c.constants):put(m,a,v)
 if raw:
  original=dict(m)
  for source,n in((packet(c),112),(damping(c),4),(rngslot(c),4)):
   for i in range(n):m[source+4+i]=original[source+i]
 return m
def snapshot(m,c):return tuple(read(m,a)for a in CONSTANTS),data(m,OUTPUT,0xac),data(m,MARK,32)
def effect(m,c,t,n,a):
 put(m,MARK,read(m,MARK)+1)
 if t==RNG:
  if c.mode&1:
   if n==1:put(m,CONSTANTS[0],bits(500.))
   if n==4:put(m,CONSTANTS[2],bits(1.25));put(m,CONSTANTS[3],bits(.875))
  if c.home_mutations:
   if n==2:
    for i,v in enumerate((5.,-7.,9.)):put(m,STACK+c.phase+8+4*i,bits(v))
   if n==5:put(m,STACK+c.phase+56,0xaabbccfe)
  return c.rng[n-1]
 if t==FRNG:
  if c.mode&2:put(m,CONSTANTS[0 if n==1 else 1],bits(450. if n==1 else .125))
  return c.samples[n-1]
 if t==DIRECTION:
  for i,v in enumerate((bits(half(a[1])*.125),a[2]^0x80000000,bits(half(a[0])*.125))):put(m,a[3]+4*i,v)
  return 0x8bad0001
 if t==SUBMIT:
  if c.mode&4:put(m,CONSTANTS[3],bits(.5));put(m,OUTPUT+0xa8,0x87654321)
  return OUTPUT if c.outcome else 0
 assert t==COPY and a[2]==4
 for i,v in enumerate(data(m,a[1],4)):m[a[0]+i]=v
 return a[0]
def reference(initial,c,raw=False):
 m=dict(initial);calls=[];obs=[];counts={};fcsr=c.fcsr;out=packet(c,raw);damp=damping(c,raw)
 for i,v in enumerate(args(c)[:4]):put(m,STACK+c.phase+4*i,v)
 def store(at,value,n=4):put(m,out+at,value,n)
 def calc(a,b,op):
  nonlocal fcsr
  v,flags=arithmetic(a,b,op,fcsr&3);fcsr=(fcsr&~0x3f000)|flags;return v
 def call(t,a):
  a=tuple(map(u32,a));counts[t]=counts.get(t,0)+1;calls.append((t,a));obs.append((snapshot(m,c),data(m,out,112),data(m,STACK+c.phase,60),data(m,damp,4),fcsr));return effect(m,c,t,counts[t],a)
 store(0x1d,0x29,1);store(8,0xe03,2);store(0,0x200005);store(4,0)
 store(0xa,call(RNG,())%41+40,2);store(0xc,0);store(0x10,0)
 for at,v in[(0x18,0xb0),(0x19,0xa0),(0x1a,0x2a),(0x14,0x40),(0x15,0xb),(0x16,0x6a),(0x17,255)]:store(at,v,1)
 store(0x1b,call(RNG,())%157+100,1);store(0x1c,255,1);store(0x60,3,1);store(0x61,3,1)
 sample=call(FRNG,())
 for i in range(3):store(0x30+4*i,read(m,STACK+c.phase+8+4*i))
 value=calc(calc(sample,read(m,CONSTANTS[0]),2),bits(300.),0);store(0x28,value);store(0x2c,value)
 draw=call(RNG,());put(m,rngslot(c,raw),draw);sample=call(FRNG,());pitch=half(draw%26-25);speed=calc(calc(calc(sample,bits(500.),2),bits(1000.),0),read(m,CONSTANTS[1]),2)
 call(DIRECTION,(u32(half(c.angle)),u32(pitch),speed,out+0x48));store(0x58,0xe05);store(0x54,0)
 if call(RNG,())&1:store(0x58,read(m,out+0x58)|64)
 if call(RNG,())&1:store(0x58,read(m,out+0x58)|128)
 store(0x62,7,1);store(0x63,255,1);store(0x1e,25,2);store(0x20,10,2);store(0x22,60,2);store(0x24,read(m,CONSTANTS[2]));put(m,damp,read(m,CONSTANTS[3]))
 result=call(SUBMIT,(out,1,4,m[STACK+c.phase+59],1))
 if result:call(COPY,(result+0xa8,damp,4))
 return m,calls,obs,fcsr
class Oracle(FactoryOracle):
 def __init__(self,words,c,entry=None,memory=None,arguments=None,connected=None,raw=False):
  self.c=c;self.raw=raw;self.counts={};self.observations=[];self.fcsr=c.fcsr
  super().__init__(words,fixture(c,raw)if memory is None else memory,c,entry=ENTRY if entry is None else entry,arguments=args(c)if arguments is None else arguments,connected=connected);self.initial=dict(self.memory);self.before_f=self.f[:]
 def get(self,a,n):
  if getattr(self,'recording',False)and self.own_instruction:assert all(a+i in self.memory for i in range(n)),('Unmapped read',hex(a),n)
  return super().get(a,n)
 def execute(self,w):
  op,fmt,rt,fs,fd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
  if op==17 and fmt==16 and fn in(0,1,2):self.f[fd],flags=arithmetic(self.f[fs],self.f[rt],fn,self.fcsr&3);self.fcsr=(self.fcsr&~0x3f000)|flags
  else:super().execute(w)
  self.r[0]=0
 def record_call(self,t):
  assert t in(ENTRY,RNG,FRNG,DIRECTION,SUBMIT,COPY),hex(t);n={ENTRY:15,RNG:0,FRNG:0,DIRECTION:4,SUBMIT:5,COPY:3}[t];a=tuple(map(u32,self.arguments(n)));self.calls.append((t,a));self.events.append(('CALL',t,a));self.counts[t]=self.counts.get(t,0)+1
  if t!=ENTRY:self.observations.append((snapshot(self.memory,self.c),data(self.memory,packet(self.c,self.raw),112),data(self.memory,STACK+self.c.phase,60),data(self.memory,damping(self.c,self.raw),4),self.fcsr))
 def hook(self,t):
  value=effect(self.memory,self.c,t,self.counts[t],self.calls[-1][1])
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=u32(value)
  if t==FRNG:self.f[0]=value
def symbols():return dict(func_150ADA20=RNG,func_150ADA68=FRNG,func_15143794=DIRECTION,func_15130374=SUBMIT,memcpy=COPY,**{'D_%08X'%a:a for a in CONSTANTS})
@lru_cache(maxsize=1)
def streams():
 rows=[bound_blob(*payload(f,p.FUNCTION),symbols())for f in[p.OUT/'normalized-target.o',p.OUT/'qualified-owner/generic.o',p.OUT/'qualified-owner/generated.o',p.OUT/'original-target.o']]
 assert all(v==rows[0]for v in rows);assert rows[0]==list(struct.unpack_from('>137I',(p.ROOT/'conker/conker.us.bin').read_bytes(),0xf8f6c));return rows
def state(m):return(m.memory,m.r,m.f,m.fcsr,m.hi,m.lo,m.calls,m.observations,m.trace,m.current_pc,m.delay_of,m.condition)
def canonical(m):
 def pointer(a):
  if packet(m.c,True)<=a<packet(m.c,True)+112:return a-4
  if a==damping(m.c,True):return a-4
  return a
 calls=[]
 for t,a in m.calls:
  if m.raw:
   if t==DIRECTION:a=(*a[:3],pointer(a[3]))
   if t==SUBMIT:a=(pointer(a[0]),*a[1:])
   if t==COPY:a=(a[0],pointer(a[1]),a[2])
  calls.append((t,a))
 return(public(m.memory,m.c),calls,m.observations,m.fcsr,m.r[2],m.r[29],m.r[16:24],m.r[28:],m.f[20:],data(m.memory,rngslot(m.c,m.raw),4))
def check(ws,c,entry=None,raw=False):
 m=Oracle(ws,c,entry=entry,raw=raw).run();wanted,calls,obs,fcsr=reference(m.initial,c,raw);assert m.calls==calls,(c,'calls',m.calls,calls);assert public(m.memory,c)==public(wanted,c),(c,'memory');assert m.fcsr==fcsr,(c,'FCSR',m.fcsr,fcsr)
 assert len(m.observations)==len(obs)
 for i,(a,b)in enumerate(zip(m.observations,obs)):assert a[:4]==b[:4]and a[4]&127==b[4]&127,(c,'observation',i)
 assert m.r[2]==1 and m.r[29]==STACK+c.phase and m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:];return m
def cases():
 rows=[Case(angle=0xabcd0000|angle,slot=0x12340000|angle,mode=angle%8,fcsr=angle%4,seed=angle%16)for angle in range(256)]
 rows +=[Case(rng=rng,samples=tuple(map(bits,samples)),mode=mode,phase=phase,fcsr=rm,outcome=outcome,angle=angle)for rng,samples,mode,phase,rm,outcome,angle in itertools.product(((0,0,0,0,0),(40,156,25,1,1),(41,157,26,2,3),(0xffffffff,0x80000000,0xffffffff,1,0)),((0.,1.),(.1,-.25)),(0,7),(0,8),range(4),(0,1),(0x7fff,0x8000))]
 rows +=[Case(home_mutations=True,mode=mode,phase=phase,outcome=outcome)for mode,phase,outcome in itertools.product((0,7),(0,8),(0,1))]
 return rows
def main():
 programs=streams();raw=bound_blob(*payload(p.OUT/'selected-final/owner-candidate.o',p.FUNCTION),symbols());visits=set();count=prefixes=0
 for c in cases():
  models=[check(ws,c)for ws in programs];assert all(state(m)==state(models[0])for m in models);visits.update(models[0].visits);r=check(raw,c,raw=True);assert canonical(r)==canonical(models[0]),(c,'raw private-map equivalence');count+=1
 for c in[Case(),Case(mode=7,phase=8),Case(home_mutations=True,mode=7),Case(rng=(0,0,0,0,0),outcome=0)]:
  full=Oracle(programs[0],c).run()
  for cut in range(full.all_accesses):
   models=[]
   for ws in programs:
    m=Oracle(ws,c);m.cut=cut
    try:m.run();raise AssertionError('Missing access cut')
    except AccessBoundary:models.append(m)
   assert all(state(m)==state(models[0])for m in models);prefixes+=1
 assert visits==set(range(ENTRY,ENTRY+548,4)),set(range(ENTRY,ENTRY+548,4))-visits
 q=dict(cases_per_stream=count,retail_equal_streams=4,raw_canonical_stack_map_cases=count,executed_words=137,access_fault_quads=prefixes,all_four_rounding_modes=True,all_256_byte_angles=True,signed_halfword_angle_boundaries=True,full_sparse_guest_packet=True,guest_home_mutations_excluded_from_native=True,RNG_calls_per_case=5,float_RNG_calls_per_case=2,source_installed=p.installed(),matching_credit=0);(p.OUT/'guest.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
