"""Independent ordered full-function model and bounded original-provider execution."""
from dataclasses import dataclass,replace
from pathlib import Path
import itertools,json,struct
from tools.experiments import game_ring_emitter_151a37c0_recovery as source
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_payload_effect_factory_oracle import FactoryOracle
from tools.tests.game_quaternion_matrix_1504a140_oracle import fp
from tools.tests.game_perpendicular_offset_1519ef90_oracle import sqrt_word
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
ENTRY=source.ENTRY;OUT=source.OUT
E,P,A,T,ALTP,ALTA,CREATED,BANK=0x30000,0x50000,0x60000,0x70000,0x71000,0x72000,0x74000,0x78000
QUERY,CLEAN,COPY,FACTORY,RNG,POSITION=0x151A4E34,0x151A4E9C,0x10022EC0,0x151491F4,0x150ADA20,0x15143134
LIMIT,TIME=0x800A8D58,0x800BE9A4
s8=lambda v:((v&255)^128)-128
data=lambda m,p,n:bytes(m[p+i] for i in range(n))
public=lambda m:{p:v for p,v in m.items() if not STACK-2048<=p<STACK+512}
POINTS=((3.,4.,0.),(0.,0.,0.),(-3.,0.,-4.),(.00001,0.,0.),(.0001,0.,0.),(floating(0x38D1B718),0.,0.))
@dataclass(frozen=True)
class Case:
 cap:int=5;head:int=0;tail:int=4;count:int=4;flags:int=4;gate:int=0;hit:int=1;factory:int=1;motion:int=0
 pending:int=0x3E800000;scale:int=0x3F000000;elapsed:int=0x3F000000;value:int=0x3F800000;rate:int=0x3E800000;step:int=0x3F000000
 random:int=0xFFFFFFFF;qeffects:int=0;rng_effects:int=0;factory_effects:int=0;phase_base:int=3;phase_range:int=7;phase_value:int=250
 alias:int=0;phase:int=0;seed:int=0;rule:str='left'
def state(c):return P if c.alias==0 else E+0x10 if c.alias==1 else A+32
def fixture(c):
 m={STACK+c.phase+i:(i*17+c.seed*13+0xA5)&255 for i in range(-2048,512)}
 for base,n in((E,160),(P,80),(A,192),(T,512),(ALTP,80),(ALTA,192),(CREATED,128)):
  for i in range(n):m.setdefault(base+i,(i*19+c.seed*7+0x53)&255)
 p=state(c)
 for i in range(80):m.setdefault(p+i,(i*7+c.seed+0x37)&255)
 for b in(P,ALTP,p):
  put(m,b,T);m[b+4]=7;m[b+5]=1
  for at,v in((0x14,c.scale),(0x20,c.value),(0x24,c.rate),(0x34,0),(0x38,0),(0x3C,0),(0x40,c.pending),(0x48,c.elapsed)):put(m,b+at,v)
  put(m,b+0x18,0x8001,2);put(m,b+0x1A,3,2);m[b+0x28]=c.phase_base;m[b+0x29]=c.phase_range;m[b+0x30]=6;m[b+0x44]=c.phase_value
 if c.alias==0:
  for off,v in((0x10,1.),(0x14,-2.),(0x18,.25)):put(m,E+off,bits(v))
 put(m,T,0 if c.gate==1 else 1);m[T+0x3B]=8 if c.gate==2 else 7;put(m,T+0x1D4,BANK if c.hit else 0);m[T+0x74]=15 if c.hit==2 else 0
 put(m,E+0x94,A);put(m,E+0x98,p);put(m,E+0x1E,c.flags,2);m[E+0xC]=0xA7
 m[E+0x25]=c.cap;m[E+0x2C]=c.count&255;m[E+0x2D]=c.head;m[E+0x2E]=c.tail;m[E+0x2F]=0;m[E+0x30]=6
 put(m,LIMIT,0x38D1B717);put(m,TIME,c.step)
 return m
def query_effect(m,c,p):
 if c.qeffects&1:put(m,E+0x1E,read(m,E+0x1E,2)^8,2);m[E+0xC]^=0x35
 if c.qeffects&2:put(m,E+0x94,ALTA);put(m,E+0x98,ALTP)
 if c.qeffects&4:
  for off,v in((0x20,.75),(0x24,-.25),(0x48,1.5),(0x40,2.25)):put(m,p+off,bits(v))
 if c.qeffects&8:put(m,TIME,bits(.25))
def sample(m,c,p,out):
 query_effect(m,c,p)
 if c.hit==1:
  for i,v in enumerate(POINTS[c.motion]):put(m,out+4*i,bits(v))
 return c.hit==1
def cleanup(m):
 p=read(m,E+0x98);put(m,E+0x1E,read(m,E+0x1E,2)&0xFFFD,2);m[E+0x30]=0;m[p+0x30]|=1;m[p+0x30]|=4
def factory(m,c,p,args):
 assert args==(300,0xFFFFFFFF,10,0,5,48,m[E+0xC],0),args
 if c.factory_effects:put(m,p+0x20,bits(2.));m[p+7]^=0x5A;m[p+0x28]=17
 return CREATED if c.factory else 0
def rng(m,c,p,a,ordinal):
 old_tail=s8(m[E+0x2E])
 if c.rng_effects&1:m[p+0x44]=255;m[p+0x28]=250;m[p+0x29]=255
 if c.rng_effects&2:
  cap=m[E+0x25];m[E+0x2D]=(m[E+0x2D]+1)%cap;m[E+0x2C]=(c.seed*7+1)&255;m[E+0x2E]=(old_tail+1)%cap
 if c.rng_effects&4:put(m,a+24*old_tail,bits(9.));put(m,a+24*old_tail+12,bits(-1.25))
 if c.rng_effects&8 and ordinal==0:put(m,p+0x40,bits(1.25));put(m,TIME,bits(-.5))
 return c.random
def reference(c,initial=None,connected=False):
 m=fixture(c) if initial is None else dict(initial);p=read(m,E+0x98);a=read(m,E+0x94);actor=read(m,p);calls=[];ops=[]
 def op(x,y,k):ops.append((k,x,y));return fp(x,y,k,c.rule)
 def absolute(x):ops.append(('abs',x));return x&0x7FFFFFFF
 def less(x,y):ops.append(('lt',x,y));return floating(x)<floating(y)
 if not read(m,actor) or m[p+4]!=m[actor+0x3B]:return m,0,calls,ops
 def query():
  calls.append((QUERY,(p,E+16)))
  if connected and c.hit==1:calls.append((POSITION,(p+8,E+16,(read(m,actor+0x1D4)+(m[p+5]<<6))&0xFFFFFFFF)))
  return sample(m,c,p,E+16)
 fresh=False
 if not read(m,E+0x1E,2)&4:
  if not query():return m,1,calls,ops
  for off in(0,4,8):put(m,p+0x34+off,read(m,E+16+off))
  put(m,E+0x1E,read(m,E+0x1E,2)|4,2);fresh=True
 if not fresh and not query():
  calls.append((CLEAN,(E,)));cleanup(m);packet=data(m,p,48);calls.append((COPY,('snapshot-in',p,48),packet))
  args=(300,0xFFFFFFFF,10,0,5,48,m[E+0xC],0);calls.append((FACTORY,args));created=factory(m,c,p,args)
  if created:
   calls.append((COPY,('snapshot-out',created+0x28,48),packet))
   for i,v in enumerate(packet):m[created+0x28+i]=v
  return m,1,calls,ops
 dx=op(read(m,E+16),read(m,p+0x34),'sub');first=less(read(m,LIMIT),absolute(dx))
 dy=op(read(m,E+20),read(m,p+0x38),'sub');dz=op(read(m,E+24),read(m,p+0x3C),'sub')
 if first or less(read(m,LIMIT),absolute(dy)) or less(read(m,LIMIT),absolute(dz)):
  squared=op(op(op(dx,dx,'mul'),op(dy,dy,'mul'),'add'),op(dz,dz,'mul'),'add');ops.append(('sqrt',squared));length=sqrt_word(squared)
  put(m,p+0x40,op(read(m,p+0x40),op(length,read(m,p+0x14),'mul'),'add'))
 points=read(m,p+0x40)
 if not less(bits(1.),points):return m,1,calls,ops
 fraction=op(bits(1.),points,'div');position=[read(m,p+0x34+4*i) for i in range(3)];remaining=op(read(m,p+0x48),read(m,TIME),'add')
 time_step=op(remaining,fraction,'mul');rate=op(read(m,p+0x24),remaining,'mul');value=op(read(m,p+0x20),rate,'add')
 sx=op(dx,fraction,'mul');sy=op(dy,fraction,'mul');difference=op(read(m,p+0x20),value,'sub');sz=op(dz,fraction,'mul');value_step=op(difference,fraction,'mul')
 n=0
 while True:
  assert n<40,('model emission bound',c)
  entry=a+24*s8(m[E+0x2E])
  # Match the original three-word copy and interleaved value store.
  put(m,entry,position[0]);put(m,entry+4,position[1]);put(m,entry+12,value);put(m,entry+8,position[2])
  put(m,entry+16,read(m,p+0x18,2),2);put(m,entry+18,read(m,p+0x1A,2),2);m[entry+21]=m[p+0x44]
  calls.append((RNG,()));random=rng(m,c,p,a,n);m[p+0x44]=(m[p+0x44]+m[p+0x28]+random%(m[p+0x29]+1))&255;m[entry+20]=255
  m[E+0x2E]=(s8(m[E+0x2E])+1)&255
  if m[E+0x25]==s8(m[E+0x2E]):m[E+0x2E]=0
  m[E+0x2C]=(s8(m[E+0x2C])+1)&255
  if s8(m[E+0x2D])==s8(m[E+0x2E]):
   m[E+0x2D]=(s8(m[E+0x2D])+1)&255
   if m[E+0x25]==s8(m[E+0x2D]):m[E+0x2D]=0
   m[E+0x2C]=(s8(m[E+0x2C])-1)&255
  value=op(value,value_step,'add');position=[op(position[0],sx,'add'),op(position[1],sy,'add'),op(position[2],sz,'add')];remaining=op(remaining,time_step,'sub')
  put(m,p+0x40,op(read(m,p+0x40),bits(1.),'sub'));n+=1
  if not less(bits(1.),read(m,p+0x40)):break
 for i,v in enumerate(position):put(m,p+0x34+4*i,v)
 put(m,p+0x48,remaining);return m,1,calls,ops
def helpers():
 rom=(source.ROOT/'conker/conker.us.bin').read_bytes();code={}
 for entry,at,n in((QUERY,0x1D22E4,26),(CLEAN,0x1D234C,12),(COPY,0x22EC0,11)):
  code.update(zip(range(entry,entry+4*n,4),struct.unpack_from('>%dI'%n,rom,at)))
 return code
class Machine(FactoryOracle):
 def __init__(self,words,c,initial=None,connected=False):
  self.c=c;self.fp_ops=[];self.raw_calls=[];self.connected_mode=connected;initial=fixture(c) if initial is None else initial
  self.cached_p=read(initial,E+0x98);self.cached_a=read(initial,E+0x94);self.snapshot=STACK+c.phase+(-72 if len(words)==266 else -76)
  super().__init__(words,initial,c,entry=ENTRY,s={},arguments=(E,),connected=helpers() if connected else None)
  self.initial_regs=self.r[:];self.initial_fp=self.f[:]
 def execute(self,w):
  op,fmt,fn=w>>26,w>>21&31,w&63
  if op==0 and fn==3:
   v=self.r[w>>16&31];self.r[w>>11&31]=((v if v<0x80000000 else v-0x100000000)>>(w>>6&31))&0xFFFFFFFF;return
  if op==17 and fmt==16 and fn in(0,1,2,3,4,5,7,60):
   fs,ft,fd=w>>11&31,w>>16&31,w>>6&31;x,y=self.f[fs],self.f[ft]
   if fn<4:k=('add','sub','mul','div')[fn];self.fp_ops.append((k,x,y));self.f[fd]=fp(x,y,k,self.c.rule)
   elif fn==4:self.fp_ops.append(('sqrt',x));self.f[fd]=sqrt_word(x)
   elif fn==5:self.fp_ops.append(('abs',x));self.f[fd]=x&0x7FFFFFFF
   elif fn==7:self.fp_ops.append(('neg',x));self.f[fd]=x^0x80000000
   else:self.fp_ops.append(('lt',x,y));self.condition=floating(x)<floating(y)
   return
  return super().execute(w)
 def record_call(self,t):
  n={QUERY:2,CLEAN:1,COPY:3,FACTORY:8,RNG:0,POSITION:3}[t];args=tuple(self.arguments(n));ordinal=sum(x[0]==t for x in self.raw_calls);self.raw_calls.append((t,args))
  if t==COPY:
   if ordinal==0:assert args==(self.snapshot,self.cached_p,48),args;record=(t,('snapshot-in',args[1],48),data(self.memory,args[1],48))
   else:assert ordinal==1 and args==(CREATED+0x28,self.snapshot,48),args;record=(t,('snapshot-out',args[0],48),data(self.memory,args[1],48))
  else:record=(t,args)
  self.calls.append(record)
 def hook(self,t):
  args=self.raw_calls[-1][1];ordinal=sum(x[0]==t for x in self.raw_calls)-1;c=self.c
  if t==QUERY:value=sample(self.memory,c,self.cached_p,args[1])
  elif t==POSITION:sample(self.memory,c,self.cached_p,args[1]);value=0
  elif t==CLEAN:cleanup(self.memory);value=0
  elif t==FACTORY:value=factory(self.memory,c,self.cached_p,args)
  elif t==RNG:value=rng(self.memory,c,self.cached_p,self.cached_a,ordinal)
  else:
   assert t==COPY;packet=data(self.memory,args[1],args[2])
   for i,v in enumerate(packet):self.memory[args[0]+i]=v
   value=args[0]
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi=self.lo=0xDEADBEEF;self.r[2]=value&0xFFFFFFFF
def programs():
 return dict(retail=source.retail(),raw=bound_blob(*payload(OUT/'qualified.o',source.NAME),source.PIN['symbols']),guarded=bound_blob(*payload(OUT/'strict-fitted.o',source.NAME),source.PIN['symbols']))
def check(words,c,connected=False):
 initial=fixture(c);expected,answer,calls,ops=reference(c,initial,connected);q=Machine(words,c,initial,connected).run()
 assert public(q.memory)==public(expected),('memory',c,[(hex(p),v,q.memory.get(p)) for p,v in public(expected).items() if q.memory.get(p)!=v][:10])
 assert q.r[2]==answer and q.calls==calls,('return/calls',c,q.r[2],answer,q.calls,calls)
 assert q.fp_ops==ops,('FP sequence',c,next((i for i,(x,y) in enumerate(zip(q.fp_ops,ops)) if x!=y),min(len(q.fp_ops),len(ops))),q.fp_ops[:15],ops[:15])
 assert all(q.r[i]==q.initial_regs[i] for i in(*range(16,24),28,29,30,31)) and q.f[20:]==q.initial_fp[20:]
 return q
def cases():
 out=[]
 for flags,gate,hit,created,motion in itertools.product((0,4),range(3),range(3),(0,1),range(6)):
  out.append(Case(flags=flags,gate=gate,hit=hit,factory=created,motion=motion,seed=len(out)))
 for cap,ends,count,pending,scale in itertools.product((1,2,5,7),range(4),(-128,-1,0,1,7,127),(0x3F7FFFFF,0x3F800000,0x3F800001,0x40100000),(0,0x3F000000,0xBF000000)):
  if len(out)%3==1:pass
  head,tail=((0,0),(0,cap-1),(cap-1,0),(cap-1,cap-1))[ends]
  out.append(Case(cap=cap,head=head,tail=tail,count=count,pending=pending,scale=scale,seed=len(out)))
 for value in range(256):out.append(Case(cap=3,head=1,tail=2,count=s8(value),phase_base=value,phase_range=value,phase_value=value,pending=0x40100000,seed=value))
 for qeff,rnge,fac in itertools.product((0,1,2,4,8,15),(0,1,2,4,8,15),(0,1)):
  out.append(Case(qeffects=qeff,rng_effects=rnge,factory_effects=fac,seed=len(out)))
  out.append(Case(hit=0,qeffects=qeff,factory_effects=fac,seed=len(out)))
 for alias,flags,hit,rnge in itertools.product((1,2),(0,4),(0,1),(0,1,8)):
  out.append(Case(alias=alias,cap=2,head=0,tail=1,count=1,flags=flags,hit=hit,rng_effects=rnge,pending=0x40100000,seed=len(out)))
 for field,value,rule in itertools.product(('pending','scale','elapsed','value','rate','step'),(0x7FC12345,0x7F812345,0x80000000),('left','right')):
  out.append(replace(Case(),**{field:value},rule=rule))
 return out
def main():
 streams=programs();seen={k:set() for k in streams};count=0
 for c in cases():
  for label,w in streams.items():seen[label].update(check(w,c).visits)
  count+=1
 connected_cases=[c for c in cases() if c.alias==0 and (c.hit==1 or not c.qeffects)][::17];connected_seen=set()
 for c in connected_cases:
  for w in streams.values():connected_seen.update(check(w,c,True).visits)
 report=dict(cases_per_stream=count,connected_cases_per_stream=len(connected_cases),visited_words={k:len({pc for pc in v if ENTRY<=pc<ENTRY+4*len(streams[k])}) for k,v in seen.items()},original_query26_cleanup12_memcpy11=True,connected_helper_words=len({pc for pc in connected_seen if pc<ENTRY or pc>=ENTRY+1064}),all_48_snapshot_bytes=True,ordered_FP_operations=True,whole_function_study=True,source_installed=False,c_match_credit=0)
 (OUT/'guest-report.json').write_text(json.dumps(report,indent=2)+'\n');return report
if __name__=='__main__':main()
