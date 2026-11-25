"""Direction-vector effect: complete o32 inputs, three records and ordered FP."""
from dataclasses import dataclass,replace
from functools import lru_cache
import itertools,json,struct
from tools.experiments import game_radial_fragment_150bd954_match as p
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.game_interpolated_particle_emitter_150d1204_guest import arithmetic,fp
ENTRY,RNG,FRNG,SUBMIT=0x150bd954,0x150ada20,0x150ada68,0x15147da0
OUTPUT,MARK,DIRECTION=0x90000,0x70000,0x60000
CONSTANTS=tuple(range(0x8009ffd0,0x8009ffe8,4))
VALUES=(981668463,1142325248,1137410048,1008981770,1149124608,981668463)
bits,floating=fp.bits,fp.floating;u32=lambda v:v&0xffffffff
REQUEST_KNOWN=tuple([*range(20),21]);PAYLOAD_KNOWN=tuple(range(28));RENDER_KNOWN=tuple(range(30))
KNOWN=tuple([*REQUEST_KNOWN,*[28+i for i in PAYLOAD_KNOWN],*[60+i for i in RENDER_KNOWN]])
@dataclass(frozen=True)
class Case:
 coords:tuple=(bits(1.25),bits(-2.5),bits(3.75))
 normals:tuple=tuple(map(bits,(.25,-.5,.75,-1.,2.,-3.)))
 slot:int=0x123400e1
 rng:tuple=(0xffffffff,0xffffffff,0xffffffff)
 samples:tuple=tuple(map(bits,(.125,.375,.625)))
 constants:tuple=VALUES
 unused:tuple=(0xa1234567,0xffff8001,0x7fc12345,0x3f123456,0xffc54321,0xabcd80fe,0x987654ff,0x40000000,0x87654321,0x3f400000)
 outcome:int=1
 mode:int=0
 phase:int=0
 fcsr:int=0
 seed:int=0
 home_mutations:bool=False
 alias:int=0
def request(c):return STACK+c.phase-32
def packet(c):return STACK+c.phase-64
def render(c):return STACK+c.phase-100
def direction(c):return DIRECTION if not c.alias else request(c)if c.alias==1 else packet(c)+4 if c.alias==2 else packet(c)
def args(c):
 a,b,ox,oy,oz,angle,start,radius,style,extra=c.unused
 return tuple(map(u32,(a,b,*c.coords,ox,oy,oz,angle,start,radius,style,extra,direction(c),c.slot)))
def data(m,a,n):return bytes(m[a+i]for i in range(n))
def public(m,c):return{a:v for a,v in m.items()if not STACK+c.phase-2048<=a<STACK+c.phase+4096}
def records(m,c):return data(m,request(c),28)+data(m,packet(c),32)+data(m,render(c),32)
def fixture(c):
 home=STACK+c.phase;m={home+i:(i*17+c.seed*13+0xa5)&255 for i in range(-2048,4096)}
 for base,n in((OUTPUT-16,0xcc),(MARK,32),(DIRECTION,64)):m.update({base+i:(i*29+c.seed*11+0x5a)&255 for i in range(n)})
 for i,v in enumerate(args(c)):put(m,home+4*i,v)
 put(m,home+8,0x7fc12345);put(m,home+12,0xffc54321)
 for i,v in enumerate(c.normals):put(m,DIRECTION+(0 if i<3 else 32)+4*(i%3),v)
 for a,v in zip(CONSTANTS,c.constants):put(m,a,v)
 return m
def snapshot(m,c):return tuple(read(m,a)for a in CONSTANTS),data(m,OUTPUT,0xac),data(m,MARK,32),data(m,DIRECTION,64)
def effect(m,c,t,n,a):
 put(m,MARK,read(m,MARK)+1)
 if t==RNG:return c.rng[n-1]
 if t==FRNG:
  if c.mode&1:
   rows=(((0,.25),),((1,.5),(2,-.25),(3,.125)),((4,.75),(5,-.375)))
   for i,v in rows[n-1]:put(m,CONSTANTS[i],bits(v))
  if n==1 and c.mode&2:
   for i,v in enumerate((2.,-3.,4.)):put(m,DIRECTION+4*i,bits(v))
  if c.home_mutations:
   if n==1:
    for i,v in enumerate((5.,-7.,9.)):put(m,STACK+c.phase+8+4*i,bits(v))
    put(m,STACK+c.phase+52,DIRECTION+32)
   if n==3:put(m,STACK+c.phase+56,0xaabbccfe)
  return c.samples[n-1]
 assert t==SUBMIT
 put(m,a[0]+16,1)
 if c.mode&2:put(m,a[0],bits(7.));put(m,a[1]+16,bits(1.5));put(m,a[11],0x73)
 if c.mode&4:put(m,OUTPUT,0x12345678)
 return OUTPUT if c.outcome else 0
def reference(initial,c):
 m=dict(initial);calls=[];obs=[];counts={};fcsr=c.fcsr;q,d,h=request(c),packet(c),render(c)
 for i,v in enumerate(args(c)[:2]):put(m,STACK+c.phase+4*i,v)
 def store(base,at,v,n=4):put(m,base+at,v,n)
 def calc(a,b,op):
  nonlocal fcsr
  v,flags=arithmetic(a,b,op,fcsr&3);fcsr=(fcsr&~0x3f000)|flags;return v
 def call(t,a):
  a=tuple(map(u32,a));counts[t]=counts.get(t,0)+1;calls.append((t,a));obs.append((snapshot(m,c),records(m,c),data(m,STACK+c.phase,60),fcsr));return effect(m,c,t,counts[t],a)
 for at,v in[(0,0),(4,1),(8,0x160600),(12,3),(16,16),(20,128),(24,32)]:store(h,at,v)
 store(h,28,0,1);store(h,29,9,1);store(q,16,1);store(q,14,1,2)
 store(q,0,c.coords[0]);store(q,4,c.coords[1]);store(d,20,c.coords[1]);store(d,25,9,1);store(d,26,255,1);store(d,24,8,1);store(q,8,read(initial,STACK+c.phase+16))
 sample=call(FRNG,());speed=calc(calc(calc(sample,bits(127.),2),bits(85.),0),read(m,CONSTANTS[0]),2);normal=read(m,STACK+c.phase+52)
 for i in range(3):store(d,4+4*i,calc(read(m,normal+4*i),speed,2))
 store(d,27,call(RNG,())%86+180,1);store(q,21,(call(RNG,())&3)+3,1);store(q,12,call(RNG,())%31+39,2)
 sample=call(FRNG,());value=calc(calc(calc(sample,read(m,CONSTANTS[1]),2),read(m,CONSTANTS[2]),0),read(m,CONSTANTS[3]),2);store(d,0,value)
 sample=call(FRNG,());value=calc(calc(calc(sample,bits(356.),2),read(m,CONSTANTS[4]),0),read(m,CONSTANTS[5]),2);store(d,16,value)
 call(SUBMIT,(q,d,0,1,11,0,0,0,0,0,0,h,0,m[STACK+c.phase+59],1));return m,calls,obs,fcsr
class Oracle(FactoryOracle):
 def __init__(self,words,c,entry=None,memory=None,arguments=None,connected=None,raw=False):
  self.c=c;self.raw=raw;self.counts={};self.observations=[];self.fcsr=c.fcsr
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
  assert t in(ENTRY,RNG,FRNG,SUBMIT),hex(t);n={ENTRY:15,RNG:0,FRNG:0,SUBMIT:15}[t];a=tuple(map(u32,self.arguments(n)));self.calls.append((t,a));self.events.append(('CALL',t,a));self.counts[t]=self.counts.get(t,0)+1
  if t!=ENTRY:self.observations.append((snapshot(self.memory,self.c),records(self.memory,self.c),data(self.memory,STACK+self.c.phase,60),self.fcsr))
 def hook(self,t):
  value=effect(self.memory,self.c,t,self.counts[t],self.calls[-1][1])
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=u32(value)
  if t==FRNG:self.f[0]=value
def symbols():return dict(func_150ADA20=RNG,func_150ADA68=FRNG,func_15147DA0=SUBMIT,**{'D_%08X'%a:a for a in CONSTANTS})
@lru_cache(maxsize=1)
def streams():
 rows=[bound_blob(*payload(f,p.FUNCTION),symbols())for f in[p.OUT/'normalized-target.o',p.OUT/'qualified-owner/generic.o',p.OUT/'qualified-owner/generated.o',p.OUT/'original-target.o']]
 assert all(v==rows[0]for v in rows);assert rows[0]==list(struct.unpack_from('>122I',(p.ROOT/'conker/conker.us.bin').read_bytes(),0xeae04));return rows
def state(m):return(m.memory,m.r,m.f,m.fcsr,m.hi,m.lo,m.calls,m.observations,m.trace,m.current_pc,m.delay_of,m.condition)
def canonical(m):return state(m)
def check(ws,c,entry=None,raw=False):
 m=Oracle(ws,c,entry=entry,raw=raw).run();wanted,calls,obs,fcsr=reference(m.initial,c);assert m.calls==calls,(c,'calls',m.calls,calls);assert public(m.memory,c)==public(wanted,c),(c,'public');assert records(m.memory,c)==records(wanted,c),(c,'records');assert m.fcsr==fcsr,(c,'FCSR',m.fcsr,fcsr)
 for i,(a,b)in enumerate(zip(m.observations,obs)):assert a[:3]==b[:3]and a[3]&127==b[3]&127,(c,'observation',i)
 assert len(m.observations)==len(obs);assert m.r[2]==1 and m.r[29]==STACK+c.phase and m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:];return m
def cases():
 rows=[Case(slot=0x12340000|i,rng=(i,i+1,i+2),mode=i%8,fcsr=i%4,seed=i%16,outcome=i%2)for i in range(256)]
 rows +=[Case(rng=draws,samples=tuple(map(bits,(0.,.5,1.)if rm&1 else(.1,-.25,.67))),mode=mode,phase=8*(rm&1),fcsr=rm,outcome=outcome)for draws,mode,rm,outcome in itertools.product(((0,0,0),(85,3,30),(86,4,31),(0xffffffff,)*3,(0x80000000,)*3),(0,7),range(4),(0,1))]
 rows +=[Case(rng=(i,3,30),mode=i%8,fcsr=i%4)for i in range(86)]
 rows +=[Case(rng=(85,3,i),mode=i%8,fcsr=i%4)for i in range(31)]
 rows +=[Case(home_mutations=True,mode=mode,phase=phase,outcome=outcome)for mode,phase,outcome in itertools.product((0,7),(0,8),(0,1))]
 rows +=[Case(alias=alias,mode=mode,fcsr=rm)for alias,mode,rm in itertools.product((1,2,3),(0,7),range(4))]
 return rows
def main():
 programs=streams();raw=bound_blob(*payload(p.OUT/'selected-final/owner-candidate.o',p.FUNCTION),symbols());assert raw==programs[0];visits=set();count=prefixes=0
 for c in cases():
  models=[check(ws,c)for ws in programs];assert all(state(m)==state(models[0])for m in models);visits.update(models[0].visits);m=check(raw,c,raw=True);assert state(m)==state(models[0]);count+=1
 for c in[Case(),Case(mode=7,phase=8),Case(home_mutations=True,mode=7),Case(alias=3,rng=(0,0,0),outcome=0)]:
  full=Oracle(programs[0],c).run()
  for cut in range(full.all_accesses):
   models=[]
   for ws in programs:
    m=Oracle(ws,c);m.cut=cut
    try:m.run();raise AssertionError('Missing access cut')
    except AccessBoundary:models.append(m)
   assert all(state(m)==state(models[0])for m in models);prefixes+=1
 assert visits==set(range(ENTRY,ENTRY+488,4))
 q=dict(cases_per_stream=count,retail_equal_streams=4,raw_identical_cases=count,executed_words=122,access_fault_quads=prefixes,all_four_rounding_modes=True,all_256_slot_bytes=True,all_86_first_draw_remainders=True,all_31_lifetime_remainders=True,unsigned_modulo_and_byte_wrap=True,full_three_guest_records_bytes=92,initialized_factory_bytes=79,guest_home_and_alias_cases_excluded_from_native=True,RNG_calls_per_case=3,float_RNG_calls_per_case=3,factory_calls_per_case=1,source_installed=p.installed(),matching_credit=0);(p.OUT/'guest.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
