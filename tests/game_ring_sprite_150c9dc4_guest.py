"""Sparse particle packet, ordered opaque RNGs, direction output and exact guest faults."""
from dataclasses import dataclass
from functools import lru_cache
import itertools,json,struct
from tools.experiments import game_ring_sprite_150c9dc4_match as p
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.game_interpolated_particle_emitter_150d1204_guest import arithmetic,fp
ENTRY=0x150c9dc4;RNG=0x150ada20;FRNG=0x150ada68;DIRECTION=0x15143794;SUBMIT=0x15132a4c;RGB=0x150ccd90
OWNER=0x30000;POINT=0x50000;MARK=0x70000;OUTPUT=0x90000;SIZE=84
CONSTANTS=(0x800a0580,0x800a0584,0x800a0588,0x800a058c,0x800a0590,0x800a0594,0x800a0598,0x800a059c);VALUES=(0x3e4ccccd,0x3c23d70a,0x3dcccccd,0x3dcccccd,0x44bfa000,0xc51c4000,0x3a83126f,0x3a83126f)
bits,floating=fp.bits,fp.floating;u32=lambda v:v&0xffffffff
half=lambda v:((v&65535)^32768)-32768
KNOWN=tuple([*range(0x59),*range(0x5c,0x69),0x6a,*range(0x6c,0x71),*range(0x72,0x76)]);BEFORE_DIRECTION=tuple([*range(8),*range(0x10,0x34),*range(0x44,0x48),*range(0x50,0x54),*range(0x56,0x58)])
@dataclass(frozen=True)
class Case:
 angle:int=0xabcdeff3
 slot:int=0x123400e1
 context:int=0xabcdef02
 base:int=bits(2.)
 point:tuple=(bits(1.),bits(-2.),bits(3.))
 rng:tuple=(0xffffffff,0x80000000,81)
 samples:tuple=tuple(map(bits,(.125,.25,.375,.5,.625,.75,.875,.99)))
 constants:tuple=VALUES
 unused_sine:int=bits(.25)
 unused_cosine:int=bits(-.5)
 outcome:int=1
 mode:int=0
 phase:int=0
 fcsr:int=0
 seed:int=0
 alias:int=0
 point_override:int=0
def packet(c):return STACK+c.phase-124
def point(c):return c.point_override or(POINT if not c.alias else packet(c)+(0x28 if c.alias==1 else 0x24)if c.alias in(1,2)else OWNER+0x10)
def args(c):return tuple(map(u32,(OWNER,point(c),c.angle,c.unused_sine,c.unused_cosine)))
def data(m,a,n):return bytes(m[a+i]for i in range(n))
def public(m,c):return{a:v for a,v in m.items()if not STACK+c.phase-1024<=a<STACK+c.phase+2048}
def fixture(c):
 home=STACK+c.phase;m={home+i:(i*17+c.seed*13+0xa5)&255 for i in range(-1024,2048)}
 for base,n in((OWNER-16,SIZE+32),(POINT-16,44),(MARK,32)):
  m.update({base+i:(i*29+c.seed*11+0x5a)&255 for i in range(n)})
 put(m,OWNER+1,c.context,1);put(m,OWNER+0xc,c.slot,1);put(m,OWNER+0x20,c.base)
 for i,v in enumerate(c.point):put(m,point(c)+4*i,v)
 for a,v in zip(CONSTANTS,c.constants):put(m,a,v)
 return m
def snapshot(m,c):return data(m,OWNER,SIZE),data(m,point(c),12),tuple(read(m,a)for a in CONSTANTS),data(m,MARK,32)
def effect(m,c,t,n,a):
 put(m,MARK,read(m,MARK)+1)
 if t==RGB:
  for at,v in zip(a[1:],(88.,77.,66.)):put(m,at,bits(v))
  if c.mode&1:
   for i,v in enumerate((-1.,4.,8.)):put(m,point(c)+4*i,bits(v))
  return 0
 if t==RNG:
  if c.mode&1:
   if n==1:put(m,OWNER+0x20,bits(-3.))
   if n==2:put(m,OWNER+1,0x91,1)
   if n==3:put(m,point(c),bits(-11.))
  return c.rng[n-1]
 if t==FRNG:
  if c.mode&2:
   if n==1:
    for i,v in enumerate((5.,-7.,9.)):put(m,point(c)+4*i,bits(v))
   if n==4:put(m,OWNER+0x20,bits(4.));put(m,CONSTANTS[1],bits(.015625))
   if n==5:put(m,CONSTANTS[2],bits(.125))
   if n==6:put(m,CONSTANTS[3],bits(.25))
   if n==7:put(m,CONSTANTS[4],bits(1000.));put(m,CONSTANTS[5],bits(-1500.));put(m,CONSTANTS[6],bits(.00125))
   if n==8:put(m,CONSTANTS[7],bits(.00125))
  return c.samples[n-1]
 if t==DIRECTION:
  for i,v in enumerate((bits(half(a[1])*.125),a[2]^0x80000000,bits((a[0]&255)*.125))):put(m,a[3]+4*i,v)
  if c.mode&4:put(m,OWNER+0xc,0xa7,1);put(m,OWNER+1,0xfe,1)
  return 0x8bad0001
 assert t==SUBMIT,hex(t)
 if c.mode&8:put(m,OWNER+0x20,bits(17.));put(m,point(c),bits(-11.))
 return OUTPUT if c.outcome else 0

def reference(initial,c):
 m=dict(initial);calls=[];obs=[];counts={};fcsr=c.fcsr;out=packet(c)
 def store(at,value,n=4):put(m,out+at,value,n)
 def calc(a,b,op):
  nonlocal fcsr
  v,flags=arithmetic(a,b,op,fcsr&3);fcsr=(fcsr&~0x3f000)|flags;return v
 def call(t,a):
  a=tuple(map(u32,a));counts[t]=counts.get(t,0)+1;calls.append((t,a));obs.append((snapshot(m,c),data(m,out,124),fcsr));return effect(m,c,t,counts[t],a)
 call(RGB,(read(m,point(c)+8),out-4,out-8,out-12))
 for i in range(3):store(0x28+i*4,read(m,point(c)+i*4))
 for at in(0x1c,0x20,0x24):store(at,bits(1.))
 store(0x50,0x29e8)
 for at in(0x10,0x14,0x18):store(at,calc(call(FRNG,()),bits(360.),2))
 store(4,read(m,CONSTANTS[0]));store(0x56,32,2);store(0x44,0);store(0,bits(1.))
 pitch=half(call(RNG,())%26-45);sample=call(FRNG,());speed=calc(calc(calc(sample,bits(81.),2),bits(60.),0),read(m,OWNER+0x20),2);speed=calc(speed,read(m,CONSTANTS[1]),2)
 call(DIRECTION,(c.angle&255,u32(pitch),speed,out+0x34))
 sample=call(FRNG,());store(0x40,calc(calc(calc(sample,bits(260.),2),bits(-130.),0),read(m,CONSTANTS[2]),2))
 sample=call(FRNG,());store(0x48,calc(calc(calc(sample,bits(260.),2),bits(-130.),0),read(m,CONSTANTS[3]),2))
 store(0x54,call(RNG,())%41+40,2)
 sample=call(FRNG,());store(0x4c,calc(calc(calc(sample,read(m,CONSTANTS[4]),2),read(m,CONSTANTS[5]),0),read(m,CONSTANTS[6]),2))
 sample=call(FRNG,());value=calc(calc(calc(sample,bits(400.),2),bits(199.),0),read(m,CONSTANTS[7]),2);store(0x58,0,1);store(0x5c,0);store(8,value);store(0xc,value)
 store(0x60,call(RNG,())%101+155,1);store(0x61,7,1)
 for at in range(0x62,0x69):store(at,0,1)
 store(0x6a,2,1);store(0x6c,0);store(0x70,0,1);store(0x72,32,2);store(0x74,7,2)
 call(SUBMIT,(out,3,255,0,m[OWNER+0xc],m[OWNER+1]));return m,calls,obs,fcsr

class Oracle(FactoryOracle):
 def __init__(self,words,c,entry=None,memory=None,arguments=None,connected=None):
  self.c=c;self.counts={};self.observations=[];self.fcsr=c.fcsr
  super().__init__(words,fixture(c)if memory is None else memory,c,entry=ENTRY if entry is None else entry,arguments=args(c)if arguments is None else arguments,connected=connected);self.initial=dict(self.memory);self.before_f=self.f[:]
 def get(self,a,n):
  if getattr(self,'recording',False)and self.own_instruction:assert all(a+i in self.memory for i in range(n)),('Unmapped read',hex(a),n)
  return super().get(a,n)
 def execute(self,w):
  op,fmt,rt,fs,fd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
  if op==17 and fmt==16 and fn in(0,1,2):self.f[fd],flags=arithmetic(self.f[fs],self.f[rt],fn,self.fcsr&3);self.fcsr=(self.fcsr&~0x3f000)|flags
  else:super().execute(w)
  self.r[0]=0
 def record_call(self,t):
  assert t in(ENTRY,RNG,FRNG,DIRECTION,SUBMIT,RGB),hex(t);n={ENTRY:5,RNG:0,FRNG:0,DIRECTION:4,SUBMIT:6,RGB:4}[t];a=tuple(map(u32,self.arguments(n)))
  if t==RGB:a=(self.f[12],*a[1:])
  self.calls.append((t,a));self.events.append(('CALL',t,a));self.counts[t]=self.counts.get(t,0)+1
  if t!=ENTRY:self.observations.append((snapshot(self.memory,self.c),data(self.memory,packet(self.c),124),self.fcsr))
 def hook(self,t):
  value=effect(self.memory,self.c,t,self.counts[t],self.calls[-1][1])
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=u32(value)
  if t==FRNG:self.f[0]=value
@lru_cache(maxsize=1)
def streams():
 symbols=dict(func_150ADA20=RNG,func_150ADA68=FRNG,func_15143794=DIRECTION,func_15132A4C=SUBMIT,func_150CCD90=RGB,**{'D_%08X'%a:a for a in CONSTANTS});rows=[]
 for f in[p.OUT/'normalized-target.o',p.OUT/'qualified-owner/generic.o',p.OUT/'qualified-owner/generated.o',p.OUT/'original-target.o']:rows.append(bound_blob(*payload(f,p.FUNCTION),symbols))
 assert all(v==rows[0]for v in rows);assert rows[0]==list(struct.unpack_from('>174I',(p.ROOT/'conker/conker.us.bin').read_bytes(),0xf7274));return rows
def state(m):return(m.memory,m.r,m.f,m.fcsr,m.hi,m.lo,m.calls,m.observations,m.trace,m.current_pc,m.delay_of,m.condition)
def check(ws,c,entry=None):
 m=Oracle(ws,c,entry=entry).run();wanted,calls,obs,fcsr=reference(m.initial,c);assert m.calls==calls,(c,'calls',m.calls,calls);assert public(m.memory,c)==public(wanted,c),(c,'memory');assert m.fcsr==fcsr,(c,'FCSR',m.fcsr,fcsr)
 for i,(a,b)in enumerate(zip(m.observations,obs)):assert a[:2]==b[:2]and a[2]&127==b[2]&127,(c,'observation',i,a[2],b[2])
 assert m.r[29]==STACK+c.phase and m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:];return m
def cases():
 rows=[Case(angle=0xabcdef00|angle,mode=angle%16,fcsr=angle%4,slot=angle,context=255-angle,seed=angle%16)for angle in range(256)]
 rows += [Case(rng=rng,samples=tuple(map(bits,samples)),base=bits(base),mode=mode,phase=phase,fcsr=rm,outcome=outcome)for rng,samples,base,mode,phase,rm,outcome in itertools.product(((0,0,0),(25,40,100),(26,41,101),(0xffffffff,0x80000000,0xffffffff)),((0.,.125,.25,.375,.5,.625,.75,1.),(.1,-.25,.75,.33,.67,.1,.9,.5)),(0.,-2.),(0,15),(0,8),range(4),(0,1))]
 rows += [Case(alias=alias,mode=mode,phase=8,unused_sine=0x7fc12345,unused_cosine=0xffc54321)for alias,mode in itertools.product((1,2,3),(0,3,12,15))]
 return rows
def main():
 programs=streams();visits=set();count=0;prefixes=0
 for c in cases():
  models=[check(ws,c)for ws in programs];assert all(state(m)==state(models[0])for m in models);visits.update(models[0].visits);count+=1
 for c in[Case(),Case(mode=15,phase=8),Case(alias=2,mode=3),Case(rng=(0,0,0),outcome=0)]:
  full=Oracle(programs[0],c).run()
  for cut in range(full.all_accesses):
   models=[]
   for ws in programs:
    m=Oracle(ws,c);m.cut=cut
    try:m.run();raise AssertionError('Missing access cut')
    except AccessBoundary:models.append(m)
   assert all(state(m)==state(models[0])for m in models);prefixes+=1
 assert visits==set(range(ENTRY,ENTRY+696,4)),set(range(ENTRY,ENTRY+696,4))-visits
 q=dict(cases_per_stream=count,streams=4,executed_words=174,access_fault_quads=prefixes,all_four_rounding_modes=True,all_256_angles=True,finite_bounded_IEEE_model=True,full_sparse_guest_packet=True,guest_overlap_only=True,RNG_calls_per_case=3,float_RNG_calls_per_case=8,source_installed=p.installed(),matching_credit=0);(p.OUT/'guest.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
