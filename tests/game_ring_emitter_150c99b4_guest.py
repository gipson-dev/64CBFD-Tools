"""Sparse particle packet, ordered opaque RNGs, direction output and exact guest faults."""
from dataclasses import dataclass
from functools import lru_cache
import itertools,json,struct
from tools.experiments import game_ring_emitter_150c99b4_match as p
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.game_interpolated_particle_emitter_150d1204_guest import arithmetic,fp
ENTRY=0x150c99b4;RNG=0x150ada20;FRNG=0x150ada68;DIRECTION=0x15143794;SUBMIT=0x15130374
OWNER=0x30000;POINT=0x50000;MARK=0x70000;OUTPUT=0x90000;SIZE=84
CONSTANTS=(0x800a0570,0x800a0574,0x800a0578,0x800a057c);VALUES=(0x44098000,0x3a83126f,0x3e78d4ff,0x3f760419)
bits,floating=fp.bits,fp.floating;u32=lambda v:v&0xffffffff
half=lambda v:((v&65535)^32768)-32768
KNOWN=tuple([*range(0x5c),*range(0x60,0x64)]);BEFORE_DIRECTION=tuple(i for i in KNOWN if not 0x48<=i<0x54)
@dataclass(frozen=True)
class Case:
 angle:int=0xabcdeff3
 slot:int=0x123400e1
 context:int=0xabcdef02
 base:int=bits(2.)
 point:tuple=(bits(1.),bits(-2.),bits(3.))
 rng:tuple=(0xffffffff,0x80000000,1,0,81)
 samples:tuple=(bits(.125),bits(.75),bits(.375))
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
def packet(c):return STACK+c.phase-112
def point(c):return c.point_override or(POINT if not c.alias else packet(c)+(0x30 if c.alias==1 else 0x2c)if c.alias in(1,2)else OWNER+0x10)
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
 if t==RNG:
  if c.mode&1:
   if n==1:
    for i,v in enumerate((-1.,4.,8.)):put(m,point(c)+4*i,bits(v))
   if n==4:put(m,OWNER+0x20,bits(-3.));put(m,OWNER+1,0x91,1)
  return c.rng[n-1]
 if t==FRNG:
  if c.mode&2:
   if n==1:
    for i,v in enumerate((5.,-7.,9.)):put(m,point(c)+4*i,bits(v))
   if n==2:put(m,CONSTANTS[0],bits(400.));put(m,CONSTANTS[1],bits(.00125))
   if n==3:put(m,OWNER+0x20,bits(4.));put(m,CONSTANTS[2],bits(.5));put(m,CONSTANTS[3],bits(.75))
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
  a=tuple(map(u32,a));counts[t]=counts.get(t,0)+1;calls.append((t,a));obs.append((snapshot(m,c),data(m,out,112),fcsr));return effect(m,c,t,counts[t],a)
 store(0x1d,0x26,1);store(8,0xc01,2);store(0,0x200005);store(4,0)
 value=call(RNG,());store(0xa,value%81+25,2);store(0xc,0);store(0x10,0);store(0x60,5,1);store(0x61,5,1)
 for at,v in[(0x14,0),(0x15,0),(0x16,0),(0x17,255),(0x18,0),(0x19,0),(0x1a,0)]:store(at,v,1)
 value=call(RNG,());store(0x1b,value%156+100,1);store(0x1c,255,1)
 sample=call(FRNG,());value=calc(calc(sample,bits(500.),2),bits(500.),0);store(0x2c,value);store(0x28,value)
 for i in range(3):store(0x30+i*4,read(m,point(c)+i*4))
 for at in(0x3c,0x40,0x44):store(at,0)
 sample=call(FRNG,());value=calc(calc(calc(sample,read(m,CONSTANTS[0]),2),bits(-1416.),0),read(m,CONSTANTS[1]),2)
 store(0x1e,20,2);store(0x20,12,2);store(0x22,0,2);store(0x24,bits(1.));store(0x54,value)
 first=64 if call(RNG,())&1 else 0;second=128 if call(RNG,())&1 else 0;store(0x58,second|7|first|512);store(0x62,255,1);store(0x63,255,1)
 pitch=half(call(RNG,())%11-18);sample=call(FRNG,());base=read(m,OWNER+0x20);speed=calc(calc(sample,calc(base,read(m,CONSTANTS[2]),2),2),calc(base,read(m,CONSTANTS[3]),2),0)
 call(DIRECTION,(c.angle&255,u32(pitch),speed,out+0x48));call(SUBMIT,(out,1,0,m[OWNER+0xc],m[OWNER+1]));return m,calls,obs,fcsr

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
  assert t in(ENTRY,RNG,FRNG,DIRECTION,SUBMIT),hex(t);n={ENTRY:5,RNG:0,FRNG:0,DIRECTION:4,SUBMIT:5}[t];a=tuple(map(u32,self.arguments(n)));self.calls.append((t,a));self.events.append(('CALL',t,a));self.counts[t]=self.counts.get(t,0)+1
  if t!=ENTRY:self.observations.append((snapshot(self.memory,self.c),data(self.memory,packet(self.c),112),self.fcsr))
 def hook(self,t):
  value=effect(self.memory,self.c,t,self.counts[t],self.calls[-1][1])
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=u32(value)
  if t==FRNG:self.f[0]=value
@lru_cache(maxsize=1)
def streams():
 symbols=dict(func_150ADA20=RNG,func_150ADA68=FRNG,func_15143794=DIRECTION,func_15130374=SUBMIT,**{'D_%08X'%a:a for a in CONSTANTS});rows=[]
 for f in[p.OUT/'normalized-target.o',p.OUT/'qualified-owner/generic.o',p.OUT/'qualified-owner/generated.o',p.OUT/'original-target.o']:rows.append(bound_blob(*payload(f,p.FUNCTION),symbols))
 assert all(v==rows[0]for v in rows);assert rows[0]==list(struct.unpack_from('>138I',(p.ROOT/'conker/conker.us.bin').read_bytes(),0xf6e64));return rows
def state(m):return(m.memory,m.r,m.f,m.fcsr,m.hi,m.lo,m.calls,m.observations,m.trace,m.current_pc,m.delay_of,m.condition)
def check(ws,c,entry=None):
 m=Oracle(ws,c,entry=entry).run();wanted,calls,obs,fcsr=reference(m.initial,c);assert m.calls==calls,(c,'calls',m.calls,calls);assert public(m.memory,c)==public(wanted,c),(c,'memory');assert m.fcsr==fcsr,(c,'FCSR',m.fcsr,fcsr)
 for i,(a,b)in enumerate(zip(m.observations,obs)):assert a[:2]==b[:2]and a[2]&127==b[2]&127,(c,'observation',i,a[2],b[2])
 assert m.r[29]==STACK+c.phase and m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:];return m
def cases():
 rows=[Case(angle=0xabcdef00|angle,mode=angle%16,fcsr=angle%4,slot=angle,context=255-angle,seed=angle%16)for angle in range(256)]
 rows += [Case(rng=(a,b,c,d,e),samples=tuple(map(bits,samples)),base=bits(base),mode=mode,phase=phase,fcsr=rm,outcome=outcome)for (a,b,c,d,e),samples,base,mode,phase,rm,outcome in itertools.product(((0,0,0,0,0),(80,155,1,1,10),(81,156,2,3,11),(0xffffffff,0x80000000,0,1,0xffffffff)),((0.,.5,1.),(.1,-.25,.75)),(0.,-2.),(0,15),(0,8),range(4),(0,1))]
 rows += [Case(alias=alias,mode=mode,phase=8,unused_sine=0x7fc12345,unused_cosine=0xffc54321)for alias,mode in itertools.product((1,2,3),(0,3,12,15))]
 return rows
def main():
 programs=streams();visits=set();count=0;prefixes=0
 for c in cases():
  models=[check(ws,c)for ws in programs];assert all(state(m)==state(models[0])for m in models);visits.update(models[0].visits);count+=1
 for c in[Case(),Case(mode=15,phase=8),Case(alias=2,mode=3),Case(rng=(0,0,0,0,0),outcome=0)]:
  full=Oracle(programs[0],c).run()
  for cut in range(full.all_accesses):
   models=[]
   for ws in programs:
    m=Oracle(ws,c);m.cut=cut
    try:m.run();raise AssertionError('Missing access cut')
    except AccessBoundary:models.append(m)
   assert all(state(m)==state(models[0])for m in models);prefixes+=1
 assert visits==set(range(ENTRY,ENTRY+552,4)),set(range(ENTRY,ENTRY+552,4))-visits
 q=dict(cases_per_stream=count,streams=4,executed_words=138,access_fault_quads=prefixes,all_four_rounding_modes=True,all_256_angles=True,finite_bounded_IEEE_model=True,full_sparse_guest_packet=True,guest_overlap_only=True,RNG_calls_per_case=5,float_RNG_calls_per_case=3,source_installed=p.installed(),matching_credit=0);(p.OUT/'guest.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
