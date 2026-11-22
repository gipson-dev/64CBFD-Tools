"""Bounded IEEE accumulation, escaped packet effects, allocation outcomes and faults."""
from pathlib import Path
from dataclasses import dataclass,replace
from functools import lru_cache
import itertools,json,struct,sys
from tools.experiments import game_particle_emission_accumulator_150ec520_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests import game_interpolated_particle_emitter_150d1204_guest as fp
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
ENTRY=0x150EC520;GATE_FN=0x151464B8;FRNG=0x150ADA68;RNG=0x150ADA20;SAMPLE=0x151432BC;FACTORY=0x15149130;COPY=0x10022EC0
RECORD=0x30000;SOURCE=0x50000;OTHER=0x51000;GATE=0x52000;ALT_GATE=0x52100;OUTPUT=0x60000
BASE=0x800A1570;SPREAD=0x800A1574;STEP=0x800BE9A4;GLOBALS=(BASE,SPREAD,STEP)
bits,floating,u32=fp.bits,fp.floating,fp.u32
half=lambda v:((v&65535)^32768)-32768
@dataclass(frozen=True)
class Case:
 gate_result:int=0
 accumulator:int=bits(2.25)
 rate:int=bits(1.)
 constants:tuple=(bits(.5),bits(1.),bits(.5))
 random_float:int=bits(.5)
 randoms:tuple=(0,1,130,131,0x80000000,0xFFFFFFFF,255,0x7FFFFFFF)
 allocation_mask:int=0xFF
 kind:int=0xAB
 context:int=0xCD
 mode:int=0
 phase:int=0
 fcsr:int=0
 rng_flags:int=0
 sample_flags:object=None
def packet_address(home):return home-20
def fixture(c):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-2048,512)}
 m.update({RECORD+i:0xA5 for i in range(-16,72)})
 for p in(SOURCE,OTHER,GATE,ALT_GATE):m.update({p+i:0xA5 for i in range(32)})
 for p,values in((SOURCE,(1,2,3,4)),(OTHER,(16,32,48,8))):
  for off,value in zip((0,2,4,8),values):put(m,p+off,value,2)
  m[p+0x15]=3
 put(m,GATE,0,2);put(m,GATE+2,1,2);put(m,ALT_GATE,0,2);put(m,ALT_GATE+2,0,2)
 m[RECORD+1]=c.context;m[RECORD+0xC]=c.kind;m[RECORD+0xD]=0;put(m,RECORD+0xE,1000,2);m[RECORD+0x10]=255;m[RECORD+0x11]=89
 for off,v in((0x28,SOURCE),(0x2C,c.rate),(0x30,GATE),(0x34,c.accumulator)):put(m,RECORD+off,v)
 for p,v in zip(GLOBALS,c.constants):put(m,p,v)
 m.update({OUTPUT+i:0xA5 for i in range(8*64)})
 return m
def public(m):return{a:v for a,v in m.items()if not STACK-2048<=a<STACK+512}
def hash_bytes(values):
 h=2166136261
 for v in values:h=((h^v)*16777619)&0xFFFFFFFF
 return h
def snapshot(m):
 values=[hash_bytes(m[RECORD+i]for i in range(40)),*(read(m,RECORD+i)for i in(0x28,0x2C,0x30,0x34)),*(read(m,p)for p in GLOBALS)]
 for n in range(8):
  p=OUTPUT+64*n;values +=[hash_bytes(m[p+i]for i in range(40)),*(read(m,p+40+4*i)for i in range(4))]
 return tuple(values)
def observe(m,home,valid,fcsr):
 p=packet_address(home);return(snapshot(m),valid,tuple(read(m,p+4*i)if valid&(1<<i)else 0 for i in range(4)),read(m,p-4)if valid&16 else 0,fcsr)
def initialize(m,p,args):
 put(m,p+14,args[0],2)
 for off,v in((13,args[4]),(16,args[1]),(17,args[2]),(18,args[3]),(19,args[5])):m[p+off]=v&255
 for i in range(16):m[p+20+i]=0
def sample(m,args):
 source,x,z,top,y=args;values={off:half(read(m,source+off,2))for off in(0,2,4,8)}
 for p,v in((x,values[0]),(z,values[4]),(top,values[2]+values[8]),(y,values[2]-values[8])):put(m,p,bits(float(v)))
def effect(m,c,t,args,ordinal,home):
 p=packet_address(home)
 if t==GATE_FN:
  if c.mode&1:put(m,RECORD+0x2C,bits(.5));put(m,RECORD+0x30,ALT_GATE);put(m,BASE,bits(.25))
  return c.gate_result
 if t==FRNG:
  if c.mode&2:
   for at,v in zip(GLOBALS,(2.,.5,.25)):put(m,at,bits(v))
   put(m,RECORD+0x2C,bits(.75))
  return c.random_float
 if t==SAMPLE:
  sample(m,args)
  if c.mode&4:put(m,RECORD+0x28,OTHER);m[RECORD+0xC]^=0x55
  return 0
 if t==RNG:
  if c.mode&8:put(m,p+12,bits(float(ordinal)));m[RECORD+1]=(c.context+ordinal)&255
  return c.randoms[(ordinal-1)%len(c.randoms)]
 if t==FACTORY:
  if c.mode&16:put(m,p,bits(float(-ordinal)));m[RECORD+0xC]=(c.kind+ordinal)&255
  answer=OUTPUT+64*(ordinal-1)if c.allocation_mask&(1<<(ordinal-1))else 0
  if answer:initialize(m,answer,args)
  return answer
 assert t==COPY and args[2]==16
 for i in range(args[2]):m[args[0]+i]=m[args[1]+i]
 if c.mode&32 and ordinal==1:put(m,RECORD+0x34,bits(.5))
 return args[0]
def reference(initial,c,provider=None,home=None):
 home=STACK+c.phase if home is None else home;m=dict(initial);calls=[];observations=[];counts={};fcsr=c.fcsr;valid=0;p=packet_address(home)
 def calc(a,b,fn):
  nonlocal fcsr
  result,flags=fp.arithmetic(a,b,fn,fcsr&3);fcsr=(fcsr&~0x3F000)|flags;return result
 def call(t,*args):
  nonlocal fcsr
  args=tuple(map(u32,args));counts[t]=counts.get(t,0)+1;calls.append((t,args));observations.append(observe(m,home,valid,fcsr))
  value=effect(m,c,t,args,counts[t],home)if provider is None else provider(m,c,t,args,counts[t],home)
  if t==FRNG:fcsr=(fcsr&~0x3F000)|c.rng_flags
  if t==SAMPLE and c.sample_flags is not None:fcsr=(fcsr&~0x3F000)|c.sample_flags
  return value
 if call(GATE_FN,read(m,RECORD+0x30))==0:
  draw=call(FRNG)
  increment=calc(calc(calc(read(m,BASE),calc(draw,read(m,SPREAD),2),0),read(m,RECORD+0x2C),2),read(m,STEP),2)
  put(m,RECORD+0x34,calc(read(m,RECORD+0x34),increment,0))
  if floating(read(m,RECORD+0x34))>1.:
   put(m,p+12,0);valid=8
   for iteration in range(8):
    call(SAMPLE,read(m,RECORD+0x28),p,p+8,p-4,p+4);valid=31
    lifetime=call(RNG)%131+80
    answer=call(FACTORY,lifetime,-1,90,-1,1,0,16,m[RECORD+0xC],m[RECORD+1])
    if answer:call(COPY,answer+40,p,16)
    put(m,RECORD+0x34,calc(read(m,RECORD+0x34),bits(1.),1))
    if not floating(read(m,RECORD+0x34))>1.:break
   else:raise AssertionError('reference exceeded bounded emission count')
 return m,calls,observations,fcsr
class Oracle(fp.Oracle):
 def __init__(self,words,c,entry=ENTRY,connected=None,memory=None,arguments=None):
  self.c=c;self.home=STACK+c.phase
  FactoryOracle.__init__(self,words,fixture(c)if memory is None else memory,c,entry=entry,arguments=(RECORD,)if arguments is None else arguments,connected=connected)
  self.initial=dict(self.memory);self.before_f=self.f[:];self.fcsr=c.fcsr;self.counts={};self.observations=[]
 def record_call(self,t):
  counts={GATE_FN:1,FRNG:0,RNG:0,SAMPLE:5,FACTORY:9,COPY:3,ENTRY:1};assert t in counts,hex(t)
  args=tuple(map(u32,self.arguments(counts[t])))
  if t==ENTRY:self.home=self.r[29]
  valid=(8 if self.counts.get(SAMPLE,0)==0 else 31)if t==SAMPLE else 31 if self.counts.get(SAMPLE,0)else 0
  self.calls.append((t,args));self.events.append(('CALL',t,args));self.counts[t]=self.counts.get(t,0)+1;self.observations.append(observe(self.memory,self.home,valid,self.fcsr))
 def clobber(self,value):
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(value)
 def hook(self,t):
  value=effect(self.memory,self.c,t,self.calls[-1][1],self.counts[t],self.home);self.clobber(value)
  if t==FRNG:self.f[0]=value;self.fcsr=(self.fcsr&~0x3F000)|self.c.rng_flags
  if t==SAMPLE and self.c.sample_flags is not None:self.fcsr=(self.fcsr&~0x3F000)|self.c.sample_flags
@lru_cache(maxsize=1)
def streams():
 words=json.loads((out/'program.json').read_text());truth=list(struct.unpack_from('>100I',(root/'conker/conker.us.bin').read_bytes(),0x1199D0));assert words==truth;return words,truth
def state(m):return(m.memory,m.r,m.f,m.fcsr,m.hi,m.lo,m.calls,m.observations,m.trace,m.current_pc,m.delay_of,m.condition)
def check(words,c):
 m=Oracle(words,c).run();expected,calls,observations,fcsr=reference(m.initial,c)
 assert m.calls==calls,(c,'calls',m.calls,calls)
 assert m.observations==observations,(c,'ordered snapshots',[(i,a,b)for i,(a,b)in enumerate(zip(m.observations,observations))if a!=b][:1])
 assert public(m.memory)==public(expected),(c,'memory')
 assert m.fcsr==fcsr,(c,'bounded FCSR',m.fcsr,fcsr)
 assert m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:]
 return m
def cases():
 yield from(Case(gate_result=gate,mode=mode,phase=phase)for gate,mode,phase in itertools.product((1,128,255),(0,63),(0,8)))
 yield from(Case(accumulator=bits(a),rate=bits(rate),mode=mode,allocation_mask=mask,phase=phase,fcsr=rm)for a,rate,mode,mask,phase,rm in itertools.product((0.,1.,1.0000001192092896,2.,5.25),(0.,1.),(0,3,12,24,32,63),(0,0x55,0xFF),(0,8),range(4)))
 yield from(Case(randoms=(v,)*8,kind=k,context=255-k)for v,k in itertools.product((0,1,130,131,0x7FFFFFFF,0x80000000,0xFFFFFFFF),(0,255)))
 yield from(Case(accumulator=zero,rate=zero,constants=(zero,zero,zero),random_float=zero,fcsr=rm)for zero,rm in itertools.product((0,0x80000000),range(4)))
 yield from(Case(accumulator=a,constants=(0x33C221ED,0x33D3F4E6,bits(1.)),fcsr=rm)for a,rm in itertools.product((bits(0.),0x3F7FFFFF,bits(1.)),range(4)))
def main():
 visits=set();count=0
 for c in cases():
  a,b=[check(words,c)for words in streams()];assert state(a)==state(b);visits.update(a.visits);count+=1
 faults=0
 for c in(Case(gate_result=1),Case(accumulator=bits(0.)),Case(accumulator=bits(2.25),mode=63,phase=8),Case(allocation_mask=0)):
  full=check(streams()[0],c)
  for cut in range(full.all_accesses):
   pair=[]
   for words in streams():
    m=Oracle(words,c);m.cut=cut
    try:m.run();raise AssertionError('missing access cut')
    except AccessBoundary:pass
    pair.append(state(m))
   assert pair[0]==pair[1];faults+=1
 missed=[i for i in range(100)if ENTRY+4*i not in visits];assert missed==[69],missed
 r=dict(cases_per_stream=count,streams=2,body_words=100,target_executed_words=99,unexecuted_word_indices=missed,
  unreachable_constant_divisor_break=True,access_fault_pairs=faults,all_four_rounding_modes=True,signed_zero_preserved=True,
  strict_threshold_and_multiple_emissions=True,allocation_null_and_success=True,escaped_packet_and_provider_effects=True,
  finite_bounded_IEEE_model=True,source_installed=packet.installed(),matching_credit=0)
 (out/'guest.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r;return r
if __name__=='__main__':main()
