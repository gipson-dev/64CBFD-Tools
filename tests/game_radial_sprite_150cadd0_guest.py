"""Fifteen-word radial ABI, extended sprite packet and closed private stack map."""
from dataclasses import dataclass,replace
from functools import lru_cache
import itertools,json,struct
from tools.experiments import game_radial_sprite_150cadd0_match as p
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.game_interpolated_particle_emitter_150d1204_guest import arithmetic,fp
ENTRY,RNG,FRNG,DIRECTION,SUBMIT=0x150cadd0,0x150ada20,0x150ada68,0x15143794,0x15132a4c
OUTPUT,MARK=0x90000,0x70000
CONSTANTS=tuple(range(0x800a05bc,0x800a05dc,4))
VALUES=(0x3e4ccccd,0x3dcccccd,0x3dcccccd,0x3dcccccd,0xc540d000,0x3a83126f,0x44164000,0x3a83126f)
bits,floating=fp.bits,fp.floating;u32=lambda v:v&0xffffffff
half=lambda v:((v&65535)^32768)-32768
KNOWN=tuple([*range(0x59),*range(0x5c,0x69),0x6a,*range(0x6c,0x71),*range(0x72,0x76)])
BEFORE_DIRECTION=tuple([*range(8),*range(0x10,0x34),*range(0x44,0x48),*range(0x50,0x54),*range(0x56,0x58)])
@dataclass(frozen=True)
class Case:
 coords:tuple=(bits(1.25),bits(-2.5),bits(3.75))
 angle:int=0xabcd80fe
 slot:int=0x123400e1
 rng:tuple=(0xffffffff,0x80000000,0xffffffff)
 samples:tuple=tuple(map(bits,(.125,.25,.375,.5,.625)))
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

def packet(c,raw=False):return STACK+c.phase-(124 if raw else 128)
def rngslot(c,raw=False):return STACK+c.phase-136
def data(m,a,n):return bytes(m[a+i]for i in range(n))
def public(m,c):return{a:v for a,v in m.items()if not STACK+c.phase-2048<=a<STACK+c.phase+4096}

def fixture(c,raw=False):
 home=STACK+c.phase;m={home+i:(i*17+c.seed*13+0xa5)&255 for i in range(-2048,4096)}
 for base,n in((OUTPUT-16,0xcc),(MARK,32)):m.update({base+i:(i*29+c.seed*11+0x5a)&255 for i in range(n)})
 for i,v in enumerate(args(c)):put(m,home+4*i,v)
 for a,v in zip(CONSTANTS,c.constants):put(m,a,v)
 if raw:
  original=dict(m)
  for i in range(124):m[packet(c,True)+i]=original[packet(c)+i]
 return m

def snapshot(m,c):return tuple(read(m,a)for a in CONSTANTS),data(m,OUTPUT,0xac),data(m,MARK,32)

def effect(m,c,t,n,a):
 put(m,MARK,read(m,MARK)+1)
 if t==RNG:
  if c.mode&1:
   if n==1:put(m,CONSTANTS[0],bits(.375))
   if n==2:put(m,CONSTANTS[4],bits(-1500.));put(m,CONSTANTS[5],bits(.00125))
  if c.home_mutations:
   if n==1:
    for i,v in enumerate((5.,-7.,9.)):put(m,STACK+c.phase+8+4*i,bits(v))
   if n==3:put(m,STACK+c.phase+56,0xaabbccfe)
  return c.rng[n-1]
 if t==FRNG:
  if c.mode&2:
   for i,v in {1:((1,.015625),),2:((2,.125),),3:((3,.25),),4:((4,-1750.),(5,.0015)),5:((6,300.),(7,.00125))}[n]:put(m,CONSTANTS[i],bits(v))
  return c.samples[n-1]
 if t==DIRECTION:
  for i,v in enumerate((bits(half(a[1])*.125),a[2]^0x80000000,bits(half(a[0])*.125))):put(m,a[3]+4*i,v)
  return 0x8bad0001
 assert t==SUBMIT,hex(t)
 if c.mode&4:put(m,CONSTANTS[7],bits(.5));put(m,OUTPUT+0xa8,0x87654321)
 return OUTPUT if c.outcome else 0

def reference(initial,c,raw=False):
 m=dict(initial);calls=[];obs=[];counts={};fcsr=c.fcsr;out=packet(c,raw)
 for i,v in enumerate(args(c)[:2]):put(m,STACK+c.phase+4*i,v)
 def store(at,value,n=4):put(m,out+at,value,n)
 def calc(a,b,op):
  nonlocal fcsr
  v,flags=arithmetic(a,b,op,fcsr&3);fcsr=(fcsr&~0x3f000)|flags;return v
 def call(t,a):
  a=tuple(map(u32,a));counts[t]=counts.get(t,0)+1;calls.append((t,a));obs.append((snapshot(m,c),data(m,out,124),data(m,STACK+c.phase,60),fcsr));return effect(m,c,t,counts[t],a)
 for i,v in enumerate(c.coords):store(0x28+4*i,v)
 for at in(0x1c,0x20,0x24):store(at,bits(1.))
 store(0x50,0x29e8)
 for at in(0x10,0x14,0x18,0x44):store(at,0)
 store(0,bits(1.));store(0x56,32,2);store(4,read(m,CONSTANTS[0]))
 draw=call(RNG,());put(m,rngslot(c,raw),draw);sample=call(FRNG,());pitch=half(draw%21-40);speed=calc(calc(calc(sample,bits(204.),2),bits(500.),0),read(m,CONSTANTS[1]),2)
 call(DIRECTION,(u32(half(c.angle)),u32(pitch),speed,out+0x34))
 for at,index in((0x40,2),(0x48,3)):
  sample=call(FRNG,());store(at,calc(calc(calc(sample,bits(260.),2),bits(-130.),0),read(m,CONSTANTS[index]),2))
 store(0x54,call(RNG,())%51+50,2)
 sample=call(FRNG,());store(0x4c,calc(calc(calc(sample,bits(1008.),2),read(m,CONSTANTS[4]),0),read(m,CONSTANTS[5]),2))
 sample=call(FRNG,());value=calc(calc(calc(sample,read(m,CONSTANTS[6]),2),bits(200.),0),read(m,CONSTANTS[7]),2);store(0x58,0,1);store(0x5c,0);store(8,value);store(0xc,value)
 store(0x60,call(RNG,())%76+180,1);store(0x61,4,1)
 for at in range(0x62,0x69):store(at,0,1)
 store(0x6a,2,1);store(0x6c,0);store(0x70,0,1);store(0x72,32,2);store(0x74,7,2)
 call(SUBMIT,(out,3,255,0,m[STACK+c.phase+59],0));return m,calls,obs,fcsr

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
  assert t in(ENTRY,RNG,FRNG,DIRECTION,SUBMIT),hex(t);n={ENTRY:15,RNG:0,FRNG:0,DIRECTION:4,SUBMIT:6}[t];a=tuple(map(u32,self.arguments(n)));self.calls.append((t,a));self.events.append(('CALL',t,a));self.counts[t]=self.counts.get(t,0)+1
  if t!=ENTRY:self.observations.append((snapshot(self.memory,self.c),data(self.memory,packet(self.c,self.raw),124),data(self.memory,STACK+self.c.phase,60),self.fcsr))
 def hook(self,t):
  value=effect(self.memory,self.c,t,self.counts[t],self.calls[-1][1])
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=u32(value)
  if t==FRNG:self.f[0]=value

def symbols():return dict(func_150ADA20=RNG,func_150ADA68=FRNG,func_15143794=DIRECTION,func_15132A4C=SUBMIT,**{'D_%08X'%a:a for a in CONSTANTS})
@lru_cache(maxsize=1)
def streams():
 rows=[bound_blob(*payload(f,p.FUNCTION),symbols())for f in[p.OUT/'normalized-target.o',p.OUT/'qualified-owner/generic.o',p.OUT/'qualified-owner/generated.o',p.OUT/'original-target.o']]
 assert all(v==rows[0]for v in rows);assert rows[0]==list(struct.unpack_from('>142I',(p.ROOT/'conker/conker.us.bin').read_bytes(),0xf8280));return rows

def state(m):return(m.memory,m.r,m.f,m.fcsr,m.hi,m.lo,m.calls,m.observations,m.trace,m.current_pc,m.delay_of,m.condition)
def canonical(m):
 calls=[]
 for t,a in m.calls:
  if m.raw:
   if t==DIRECTION:a=(*a[:3],a[3]-4)
   if t==SUBMIT:a=(a[0]-4,*a[1:])
  calls.append((t,a))
 return(public(m.memory,m.c),calls,m.observations,m.fcsr,m.r[2],m.r[29],m.r[16:24],m.r[28:],m.f[20:],data(m.memory,rngslot(m.c,m.raw),4))

def check(ws,c,entry=None,raw=False):
 m=Oracle(ws,c,entry=entry,raw=raw).run();wanted,calls,obs,fcsr=reference(m.initial,c,raw);assert m.calls==calls,(c,'calls',m.calls,calls);assert public(m.memory,c)==public(wanted,c),(c,'memory');assert m.fcsr==fcsr,(c,'FCSR',m.fcsr,fcsr)
 assert len(m.observations)==len(obs)
 for i,(a,b)in enumerate(zip(m.observations,obs)):assert a[:3]==b[:3]and a[3]&127==b[3]&127,(c,'observation',i)
 assert m.r[2]==1 and m.r[29]==STACK+c.phase and m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:];return m

def cases():
 rows=[Case(angle=0xabcd0000|angle,slot=0x12340000|angle,mode=angle%8,fcsr=angle%4,seed=angle%16)for angle in range(256)]
 rows +=[Case(rng=rng,samples=tuple(map(bits,samples)),mode=mode,phase=phase,fcsr=rm,outcome=outcome,angle=angle)for rng,samples,mode,phase,rm,outcome,angle in itertools.product(((0,0,0),(20,50,75),(21,51,76),(0xffffffff,0x80000000,0xffffffff)),((0.,.25,.5,.75,1.),(.1,-.25,.75,.33,.67)),(0,7),(0,8),range(4),(0,1),(0x7fff,0x8000))]
 rows +=[Case(home_mutations=True,mode=mode,phase=phase,outcome=outcome)for mode,phase,outcome in itertools.product((0,7),(0,8),(0,1))]
 return rows

def main():
 programs=streams();raw=bound_blob(*payload(p.OUT/'selected-final/owner-candidate.o',p.FUNCTION),symbols());visits=set();count=prefixes=0
 for c in cases():
  models=[check(ws,c)for ws in programs];assert all(state(m)==state(models[0])for m in models);visits.update(models[0].visits);r=check(raw,c,raw=True);assert canonical(r)==canonical(models[0]),(c,'raw private-map equivalence');count+=1
 for c in[Case(),Case(mode=7,phase=8),Case(home_mutations=True,mode=7),Case(rng=(0,0,0),outcome=0)]:
  full=Oracle(programs[0],c).run()
  for cut in range(full.all_accesses):
   models=[]
   for ws in programs:
    m=Oracle(ws,c);m.cut=cut
    try:m.run();raise AssertionError('Missing access cut')
    except AccessBoundary:models.append(m)
   assert all(state(m)==state(models[0])for m in models);prefixes+=1
 assert visits==set(range(ENTRY,ENTRY+568,4)),set(range(ENTRY,ENTRY+568,4))-visits
 q=dict(cases_per_stream=count,retail_equal_streams=4,raw_canonical_stack_map_cases=count,executed_words=142,access_fault_quads=prefixes,all_four_rounding_modes=True,all_256_byte_angles=True,signed_halfword_angle_boundaries=True,full_sparse_guest_packet=True,guest_home_mutations_excluded_from_native=True,RNG_calls_per_case=3,float_RNG_calls_per_case=5,source_installed=p.installed(),matching_credit=0);(p.OUT/'guest.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
