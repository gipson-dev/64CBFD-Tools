"""Independent ring layout, ordered opaque providers and bounded IEEE arithmetic."""
from dataclasses import dataclass,replace
from fractions import Fraction
from functools import lru_cache
import itertools,json,math,struct
from tools.experiments import game_ring_effect_150c88d0_match as p
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.game_point_spray_150c71c0_guest import arithmetic
from tools.tests.game_paired_actor_initializer_151951e0_guest import bits,floating,next_up,next_down
ENTRY=0x150c88d0;ALLOC=0x15167a68;COPY=0x10022ec0;SIN=0x15047d60;COS=0x15047c00;PERIOD=0x800a0528
DESC=0x30000;OUT=0x50000;ALT=0x60000;SIZE=0x1200
u32=lambda n:n&0xffffffff
signed=lambda n:((n&0xffffffff)^0x80000000)-0x80000000
half=lambda n:((n&65535)^32768)-32768
@dataclass(frozen=True)
class Case:
 count:int=4
 lifetime:int=-123
 extra:int=24
 priority:int=0xabcdefe1
 group:int=-1
 outcome:int=1
 period:int=bits(6.283185307179586)
 mode:int=0
 phase:int=0
 seed:int=0
 alias:int=0
 fcsr:int=0
 descriptor:int=0
def descriptor(c):return c.descriptor or(DESC if not c.alias else OUT+(0x10 if c.alias==1 else 0x2c))
def args(c):return tuple(map(u32,(descriptor(c),c.extra,c.priority,c.group)))
def data(m,a,n):return bytes(m[a+i]for i in range(n))
def fixture(c):
 home=STACK+c.phase;m={home+i:(i*17+c.seed*13+0xa5)&255 for i in range(-1024,2048)}
 for base,n in((DESC-16,80),(OUT-16,SIZE+32),(ALT-16,256)):m.update({base+i:(i*29+c.seed*11+0x5a)&255 for i in range(n)})
 a=descriptor(c);put(m,a+0x14,c.count);put(m,a+0x18,c.lifetime,2);put(m,PERIOD,c.period);return m
def public(m,c):return{a:v for a,v in m.items()if not STACK+c.phase-1024<=a<STACK+c.phase+2048}
def divide(a,n,rm):
 if n==0:
  assert a&0x7fffffff;return (a&0x80000000)|0x7f800000,0x8020
 exact=Fraction(floating(a))/n;z=bits(float(exact));value=Fraction(floating(z))
 if value!=exact:
  if rm==1:z=next_down(z)if exact>0 and value>exact else next_up(z)if exact<0 and value<exact else z
  elif rm==2 and value<exact:z=next_up(z)
  elif rm==3 and value>exact:z=next_down(z)
 if exact==0:z=(a^bits(float(n)))&0x80000000
 return z,0x1004 if Fraction(floating(z))!=exact else 0
def provider(m,c,t,ordinal,a):
 d=descriptor(c)
 if t==ALLOC:
  if c.mode&1:put(m,d+0x14,3);put(m,d+0x18,0x8123,2)
  return OUT if c.outcome else 0
 if t==COPY:
  values=data(m,a[1],a[2])
  for i,v in enumerate(values):m[a[0]+i]=v
  if c.mode&2:put(m,d+0x14,5);put(m,OUT+0x24,2);put(m,OUT+0x28,0x7ffe,2);put(m,PERIOD,bits(3.))
  return a[0]
 if t==SIN:
  if c.mode&4:put(m,OUT+0x360,ALT if ordinal&1 else OUT+0x368)
  return bits((ordinal%9-4)/8.)
 assert t==COS
 if c.mode&8:put(m,OUT+0x360,OUT+0x368 if ordinal&1 else ALT);put(m,OUT+0x48,bits(.5));put(m,OUT+0x24,2)
 return bits((5-ordinal%11)/8.)
def reference(initial,c):
 m=dict(initial);calls=[];observations=[];counts={};fcsr=c.fcsr;d=descriptor(c)
 def call(t,a):
  counts[t]=counts.get(t,0)+1;a=tuple(map(u32,a));calls.append((t,a));observations.append((data(m,d,48),data(m,OUT,0x368),fcsr));return provider(m,c,t,counts[t],a)
 n=signed(read(m,d+0x14));result=call(ALLOC,(0x31,c.group,u32(c.extra+(u32(n)<<3)+(u32(n)*5<<5)+0x408),1,c.priority&255,1))
 if not result:return m,calls,observations,fcsr,0
 call(COPY,(OUT+0x10,d,48));put(m,OUT+0x360,OUT+0x368)
 n=signed(read(m,d+0x14));copied=signed(read(m,OUT+0x24));put(m,OUT+0x54,u32(OUT+(u32(n)<<3)+0x368))
 n=signed(read(m,d+0x14));put(m,OUT+0x58,u32(OUT+(u32(n)<<3)+(u32(n)*5<<4)+0x3b8))
 n=signed(read(m,d+0x14));put(m,OUT+0x40,0);put(m,OUT+0x44,0);life=read(m,OUT+0x28,2);put(m,OUT+0x364,u32(OUT+(u32(n)<<3)+(u32(n)*5<<5)+0x408));put(m,OUT+0x50,0);put(m,OUT+0x4c,life,2)
 step,flags=divide(read(m,PERIOD),copied,fcsr&3);fcsr=(fcsr&~0x3f000)|flags;put(m,OUT+0x48,step);index=offset=0;angle=0
 if copied>0:
  while True:
   value=call(SIN,(angle,));put(m,read(m,OUT+0x360)+offset,value);value=call(COS,(angle,));put(m,read(m,OUT+0x360)+offset+4,value);index+=1;offset+=8;angle,flags=arithmetic(angle,read(m,OUT+0x48),0,fcsr&3);fcsr=(fcsr&~0x3f000)|flags
   if index>=signed(read(m,OUT+0x24)):break
   assert index<16
 return m,calls,observations,fcsr,OUT
class Oracle(FactoryOracle):
 def __init__(self,words,c,entry=None,memory=None,arguments=None,connected=None):
  self.c=c;self.counts={};self.observations=[];self.fcsr=c.fcsr;super().__init__(words,fixture(c)if memory is None else memory,c,entry=ENTRY if entry is None else entry,arguments=args(c)if arguments is None else arguments,connected=connected);self.initial=dict(self.memory)
 def get(self,a,n):
  if getattr(self,'recording',False)and self.own_instruction:assert all(a+i in self.memory for i in range(n)),('Unmapped read',hex(a),n)
  return super().get(a,n)
 def execute(self,w):
  op,fmt,rt,fs,fd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
  if op==17 and fmt==20 and fn==32:self.f[fd]=bits(float(signed(self.f[fs])));self.fcsr&=~0x3f000
  elif op==17 and fmt==16 and fn in(0,3):
   if fn==0:value,flags=arithmetic(self.f[fs],self.f[rt],0,self.fcsr&3)
   else:
    n=floating(self.f[rt]);assert n==math.trunc(n);value,flags=divide(self.f[fs],int(n),self.fcsr&3)
   self.f[fd]=value;self.fcsr=(self.fcsr&~0x3f000)|flags
  elif op==17 and fmt==16 and fn==6:self.f[fd]=self.f[fs]
  else:super().execute(w)
  self.r[0]=0
 def record_call(self,t):
  counts={ENTRY:4,ALLOC:6,COPY:3,SIN:1,COS:1};assert t in counts,hex(t);a=(self.f[12],)if t in(SIN,COS)else tuple(map(u32,self.arguments(counts[t])));self.calls.append((t,a));self.events.append(('CALL',t,a));self.counts[t]=self.counts.get(t,0)+1
  if t!=ENTRY:self.observations.append((data(self.memory,descriptor(self.c),48),data(self.memory,OUT,0x368),self.fcsr))
 def hook(self,t):
  value=provider(self.memory,self.c,t,self.counts[t],self.calls[-1][1])
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=u32(value)
  if t in(SIN,COS):self.f[0]=value
@lru_cache(maxsize=1)
def streams():
 symbols={'D_800A0528':PERIOD,'func_15167A68':ALLOC,'memcpy':COPY,'sinf':SIN,'cosf':COS};rows=[]
 for f in[p.OUT/'normalized-target.o',p.OUT/'qualified-owner/generic.o',p.OUT/'qualified-owner/generated.o',p.OUT/'original-target.o']:rows.append(bound_blob(*payload(f,p.FUNCTION),symbols))
 assert all(v==rows[0]for v in rows);assert rows[0]==list(struct.unpack_from('>102I',(p.ROOT/'conker/conker.us.bin').read_bytes(),0xf5d80));return rows
def state(m):return(m.memory,m.r,m.f,m.fcsr,m.hi,m.lo,m.calls,m.observations,m.trace,m.current_pc,m.delay_of,m.condition)
def cases():
 rows=[Case(count=n,mode=mode,phase=phase,fcsr=rm,priority=0xabcdef00|tag,lifetime=(tag*257)^0x8000,seed=tag%16)for tag,(n,mode,phase,rm)in enumerate(itertools.product((0,1,2,3,7,8),range(16),(0,8),range(4)))]
 rows += [Case(outcome=0,count=n,extra=extra,group=group,priority=0xfffedcab)for n,extra,group in itertools.product((-2147483648,-1,0,1,0x7fffffff),(0,0xffffffff),(0,-1))]
 rows += [Case(count=3,alias=alias,mode=mode,fcsr=rm)for alias,mode,rm in itertools.product((1,2),(0,4,8,12),range(4))]
 return rows
def check(ws,c,entry=None):
 m=Oracle(ws,c,entry=entry).run();wanted,calls,obs,fcsr,value=reference(m.initial,c);assert(public(m.memory,c),m.calls,m.observations,m.fcsr,m.r[2])==(public(wanted,c),calls,obs,fcsr,value),(c,'Semantic mismatch');assert m.r[29]==STACK+c.phase;return m
def main():
 programs=streams();visits=set();count=0;prefixes=0
 for c in cases():
  models=[check(ws,c)for ws in programs];assert all(state(m)==state(models[0])for m in models);visits.update(models[0].visits);count+=1
 for c in[Case(outcome=0),Case(count=0),Case(count=2,mode=15,phase=8),Case(count=3,alias=2)]:
  full=Oracle(programs[0],c).run()
  for cut in range(full.all_accesses):
   models=[]
   for ws in programs:
    m=Oracle(ws,c);m.cut=cut
    try:m.run();raise AssertionError('Missing access cut')
    except AccessBoundary:models.append(m)
   assert all(state(m)==state(models[0])for m in models);prefixes+=1
 assert visits==set(range(ENTRY,ENTRY+408,4)),set(range(ENTRY,ENTRY+408,4))-visits
 q=dict(cases_per_stream=count,streams=4,executed_words=102,access_fault_quads=prefixes,all_four_rounding_modes=True,finite_bounded_IEEE_model=True,zero_count_division_observed=True,mutable_live_count_step_and_lookup=True,guest_overlap_cases=True,source_installed=p.installed(),matching_credit=0);(p.OUT/'guest.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
