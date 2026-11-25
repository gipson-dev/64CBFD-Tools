"""Private bounded o32 execution; no guard/adoption credit from this alone."""
from pathlib import Path
from dataclasses import dataclass,replace
from functools import lru_cache
import hashlib,itertools,json,struct,sys
sys.path.insert(0,str(Path.cwd()))
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_interpolated_particle_emitter_150d1204_guest import arithmetic,fp
from tools.experiments import game_dual_actor_emitter_150b37c8_match as p
o=p.OUT;r=p.ROOT;ENTRY=0x150b37c8;FRNG=0x150ada68;RNG=0x150ada20;SUBMIT=0x1513c73c;FACTORY=0x15147da0;TEMPLATE=0x80088700
ACTOR,RECORD,ALT,POSITIONS,ALTPOS,PARAM,ALTPARAM,MARK=0x30000,0x32000,0x33000,0x51000,0x61000,0x36000,0x36100,0x70000
bits,floating=fp.bits,fp.floating;u32=lambda n:n&0xffffffff;signed=lambda n:((n&0xffffffff)^0x80000000)-0x80000000
NATIVE_SOURCE='vertex-request-1-payload-1'
@dataclass(frozen=True)
class Case:
 index:int=0
 rng:tuple=(0xffffffff,0x89abcdef,2,3)
 samples:tuple=(bits(.125),bits(.875))
 height:int=bits(100.)
 previous:tuple=(bits(1.),bits(2.),bits(3.))
 context:int=PARAM
 mode:int=0
 phase:int=0
 seed:int=0
 fcsr:int=0
 outcome:int=1
 home_mutations:bool=False
 provider_float_flags:tuple=()

def home(c):return STACK+c.phase
def objects(c):return(home(c)-48,home(c)-88,home(c)-120,home(c)-152)
def arguments(c):return(ACTOR,*c.previous,c.height,c.context)
def data(m,a,n):return bytes(m[a+i]for i in range(n))
def public(m,c):return{a:v for a,v in m.items()if not home(c)-2048<=a<home(c)+4096}
def fixture(c):
 m={home(c)+i:(i*17+c.seed*13+0xa5)&255 for i in range(-2048,4096)}
 for base,n in[(ACTOR,0xa0),(RECORD,0x40),(ALT,0x40),(POSITIONS-128*20,256*20),(ALTPOS-128*20,256*20),(PARAM,32),(ALTPARAM,32),(MARK,32)]:
  m.update({base+i:(i*29+c.seed*11+0x5a)&255 for i in range(n)})
 put(m,ACTOR+0x94,POSITIONS);put(m,ACTOR+0x98,RECORD);m[ACTOR+0x2d]=c.index&255;m[ACTOR+0xc]=0xa1;m[ACTOR+1]=0xb2;m[ACTOR+0x25]=7
 for base in(POSITIONS,ALTPOS):
  for i in range(-128,128):
   for off,value in[(0,10.+i),(4,20.-i),(8,-30.-i),(12,-1.),(16,2.)]:put(m,base+20*i+off,bits(value))
 for base in(RECORD,ALT):
  for off,value in[(0,8.),(4,2.),(8,-3.),(12,4.),(16,.5)]:put(m,base+off,bits(value))
  m[base+0x19]=17;m[base+0x1a]=0xc1;m[base+0x1b]=0xd2
 for i,v in enumerate((15,16,17)):put(m,TEMPLATE+2*i,v,2)
 for i,v in enumerate(arguments(c)[4:],4):put(m,home(c)+4*i,v)
 return m

def packet_snapshots(m,c):return tuple(data(m,p,n)for p,n in zip(objects(c),(40,28,32,32)))
def observe(m,c,t):
 if t==SUBMIT:private=(data(m,objects(c)[0],40),)
 elif t==FACTORY:private=packet_snapshots(m,c)[1:]
 else:private=()
 return(public(m,c),private,data(m,home(c),24))

def effect(m,c,t,count,args):
 put(m,MARK,read(m,MARK)+1)
 if t==FRNG:
  if count==1 and c.mode&1:
   put(m,ACTOR+0x94,ALTPOS);put(m,ACTOR+0x98,ALT)
   for i,v in enumerate((100,101,102)):put(m,TEMPLATE+2*i,v,2)
  if count==2 and c.mode&8:put(m,RECORD+12,bits(-12.))
  if c.home_mutations and count==1:
   for i in(1,2,3):put(m,home(c)+4*i,0xabcd0000+i)
  return c.samples[count-1]
 if t==RNG:
  if c.mode&2:
   if count==2:m[RECORD+0x1a]=0x72;m[RECORD+0x1b]=0x83
   if count==4:
    m[ACTOR+0x2d]=255;put(m,POSITIONS-20,bits(42.));put(m,POSITIONS-12,bits(-17.));m[ACTOR+0xc]=0xc3;m[ACTOR+1]=0xd4
  if c.home_mutations and count==4:put(m,home(c)+16,bits(6.));put(m,home(c)+20,ALTPARAM)
  return u32(c.rng[count-1])
 if t==SUBMIT:
  if c.mode&4:
   m[ACTOR+0x2d]=1;put(m,POSITIONS+20,bits(123.));put(m,POSITIONS+28,bits(-82.))
   for off,value in[(0,4.),(4,7.),(12,-9.),(16,1.25)]:put(m,RECORD+off,bits(value))
   m[RECORD+0x19]=23;m[RECORD+0x1a]=0x56;m[RECORD+0x1b]=0x67;m[ACTOR+0x25]=13
  if c.mode&8:
   for i in range(40):m[args[0]+i]=(i*7+0x31)&255
  if c.home_mutations:put(m,home(c)+16,bits(-5.))
  return 0x90000 if c.outcome else 0
 assert t==FACTORY
 if c.mode&8:
  for pointer,n in[(args[0],28),(args[1],32),(args[11],32)]:
   for i in range(n):m[pointer+i]=(i*3+0x55)&255
 return 0xa0000 if c.outcome else 0

def reference(initial,c):
 m=dict(initial);d,q,p,v=objects(c);calls=[];obs=[];counts={};fcsr=c.fcsr;h=home(c)
 for i in(1,2,3):put(m,h+4*i,arguments(c)[i])
 def store(base,off,value,n=4):put(m,base+off,value,n)
 def calc(a,b,op):
  nonlocal fcsr
  value,flags=arithmetic(a,b,op,fcsr&3);fcsr=(fcsr&~0x3f000)|flags;return value
 def call(t,args=()):
  nonlocal fcsr
  args=tuple(map(u32,args));counts[t]=counts.get(t,0)+1;calls.append((t,args));obs.append((observe(m,c,t),fcsr));value=effect(m,c,t,counts[t],args)
  if t==FRNG and c.provider_float_flags:fcsr=(fcsr&~0x3f000)|c.provider_float_flags[counts[t]-1]
  return value
 choices=data(m,TEMPLATE,6);m[RECORD+0x20]=4;sample=call(FRNG);scale=calc(calc(sample,bits(50.),2),bits(50.),0);choice=call(RNG)%3
 for off,value,n in[(8,0,4),(12,0,4),(0,17,4),(4,150,2),(6,int.from_bytes(choices[2*choice:2*choice+2],'big'),1),(16,m[RECORD+0x1b],1),(17,m[RECORD+0x1a],1),(18,0,1),(19,0,1),(20,0,1),(21,255,1),(24,0x30002,4)]:store(d,off,value,n)
 first=call(RNG);second=call(RNG);third=call(RNG);idx=((m[ACTOR+0x2d]^128)-128);at=POSITIONS+20*idx
 call(SUBMIT,(d,1,0,read(m,h+20),read(m,at),read(m,h+16),read(m,at+8),scale,scale,first&255,(third&1)+(second&1),0,m[ACTOR+0xc],m[ACTOR+1]))
 for off,value,n in[(0,0,4),(4,1,4),(8,0x160600,4),(12,3,4),(16,16,4),(20,128,4),(24,32,4),(28,0,1),(29,9,1)]:store(v,off,value,n)
 store(q,16,1);store(q,14,1,2)
 for off,value,n in[(25,m[RECORD+0x19],1),(24,8,1),(26,m[RECORD+0x1a],1),(27,m[RECORD+0x1b],1)]:store(p,off,value,n)
 idx=(m[ACTOR+0x2d]^128)-128;store(q,0,read(m,POSITIONS+20*idx));store(q,4,read(m,h+16));idx=(m[ACTOR+0x2d]^128)-128;store(q,8,read(m,POSITIONS+20*idx+8));store(q,21,m[ACTOR+0x25],1);store(q,12,60,2)
 store(p,0,calc(read(m,RECORD),bits(.75),2));store(p,16,read(m,RECORD+16));store(p,4,read(m,RECORD+4));sample=call(FRNG);store(p,8,calc(calc(sample,bits(15.),2),bits(15.),0));store(p,12,read(m,RECORD+12))
 call(FACTORY,(q,p,0,1,7,0,0,0,0,0,0,v,0,m[ACTOR+0xc],m[ACTOR+1]))
 return m,calls,obs,fcsr

class Oracle(FactoryOracle):
 def __init__(self,words,c,entry=ENTRY,memory=None,args=None,connected=None):
  self.c=c;self.fcsr=c.fcsr;self.counts={};self.observations=[]
  super().__init__(words,fixture(c)if memory is None else memory,c,entry=entry,arguments=arguments(c)if args is None else args,connected=connected);self.initial=dict(self.memory);self.before_f=self.f[:]
 def execute(self,w):
  op,fmt,rt,fs,fd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
  if op==17 and fmt==16 and fn in(0,1,2):self.f[fd],flags=arithmetic(self.f[fs],self.f[rt],fn,self.fcsr&3);self.fcsr=(self.fcsr&~0x3f000)|flags
  elif op==17 and fmt==16 and fn==60:self.condition=floating(self.f[fs])<floating(self.f[rt]);self.fcsr=(self.fcsr&~0x800000)|(0x800000 if self.condition else 0)
  else:super().execute(w)
  self.r[0]=0
 def record_call(self,t):
  n={FRNG:0,RNG:0,SUBMIT:14,FACTORY:15};assert t in n,hex(t);args=tuple(map(u32,self.arguments(n[t])));self.calls.append((t,args));self.events.append(('CALL',t,args));self.counts[t]=self.counts.get(t,0)+1;self.observations.append((observe(self.memory,self.c,t),self.fcsr))
 def hook(self,t):
  value=effect(self.memory,self.c,t,self.counts[t],self.calls[-1][1])
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=u32(value)
  if t==FRNG:self.f[0]=value

def symbols():return dict(func_150ADA20=RNG,func_150ADA68=FRNG,func_1513C73C=SUBMIT,func_15147DA0=FACTORY,D_80088700=TEMPLATE)
@lru_cache(maxsize=1)
def streams():
 rows=[bound_blob(*payload(f,p.FUNCTION),symbols())for f in[o/'normalized-target.o',o/'qualified-owner/generic.o',o/'qualified-owner/generated.o',o/'original-target.o']]
 assert all(x==rows[0]for x in rows);assert rows[0]==list(struct.unpack_from('>184I',(r/'conker/conker.us.bin').read_bytes(),0xe0c78));return rows
def state(m):return(m.memory,m.r,m.f,m.fcsr,m.hi,m.lo,m.calls,m.observations,m.trace,m.current_pc,m.delay_of,m.condition)
def check(ws,c,entry=None):
 m=Oracle(ws,c,entry=ENTRY if entry is None else entry).run();expected,calls,obs,fcsr=reference(m.initial,c)
 assert m.calls==calls,(c,'calls',m.calls,calls);assert public(m.memory,c)==public(expected,c),(c,'public');assert packet_snapshots(m.memory,c)==packet_snapshots(expected,c),(c,'packets');assert m.fcsr==fcsr,(c,'FCSR',m.fcsr,fcsr)
 assert len(m.observations)==len(obs)
 for i,(actual,wanted)in enumerate(zip(m.observations,obs)):assert actual==wanted,(c,'observation',i)
 assert m.r[2]==1 and m.r[29]==home(c)and m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:]
 return m
def cases():
 rows=[Case(index=i,rng=(u32(i),0xabcdef00|(i&255),i&1,(i>>1)&1),mode=i%16,phase=(i&1)*8,fcsr=i%4,seed=i%16,outcome=i&1)for i in range(-128,128)]
 rows +=[Case(rng=(choice,first,parity&1,(parity>>1)&1),mode=mode,fcsr=rm)for choice,first,parity,mode,rm in itertools.product((0,1,2,3,0x80000000,0xffffffff),(0,0xffffffff),range(4),(0,15),range(4))]
 rows +=[Case(home_mutations=True,mode=mode,phase=phase,outcome=outcome)for mode,phase,outcome in itertools.product((0,15),(0,8),(0,1))]
 rows +=[Case(samples=(bits(a),bits(b)),mode=mode,fcsr=rm)for a,b,mode,rm in itertools.product((.1,.3),(.1,.3),(0,15),range(4))]
 return rows
def main():
 programs=streams();raw=bound_blob(*payload(o/'selected-final/owner-candidate.o',p.FUNCTION),symbols());visits=set();count=prefixes=0
 for c in cases():
  models=[check(ws,c)for ws in programs];assert all(state(m)==state(models[0])for m in models[1:])
  other=check(raw,c);a=models[0];assert(a.calls,a.observations,a.r,a.f,a.fcsr)==(other.calls,other.observations,other.r,other.f,other.fcsr);visits|=set(a.visits);count+=1
 from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
 for c in[Case(),Case(mode=15,phase=8),Case(mode=15,home_mutations=True),Case(index=-128,outcome=0)]:
  full=Oracle(programs[0],c).run()
  for cut in range(full.all_accesses):
   models=[]
   for ws in programs:
    model=Oracle(ws,c);model.cut=cut
    try:model.run();raise AssertionError('Missing access cut')
    except AccessBoundary:models.append(model)
   assert all(state(m)==state(models[0])for m in models[1:]);prefixes+=1
 assert visits==set(range(ENTRY,ENTRY+184*4,4))
 q=dict(cases_per_stream=count,retail_equal_streams=4,raw_C_observable_state_cases=count,executed_words=184,body_words=184,slot_words=186,alignment_words=2,alignment_words_unreachable=True,all_signed_byte_indices=True,all_choice_remainders_and_parity_pairs=True,all_four_rounding_modes=True,finite_inexact_rounding_cases=True,access_fault_quads=prefixes,raw_private_spill_and_fault_order_not_claimed_equal=True,first_descriptor_bytes=40,secondary_packet_bytes=[28,32,32],first_initialized_bytes=25,secondary_initialized_bytes=75,six_template_bytes_captured_before_providers=True,helper_calls_per_case=8,source_installed=p.installed(),matching_credit=0)
 (o/'guest.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
