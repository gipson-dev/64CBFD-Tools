"""Private independent emitter model. No adoption or match credit."""
from dataclasses import dataclass,replace
from pathlib import Path
from functools import lru_cache
import itertools,json,struct
from tools.tests.game_owner_float_payload_oracle import FactoryOracle,Case as BaseCase
from tools.tests.game_quaternion_matrix_1504a140_oracle import fp
from tools.tests.game_perpendicular_offset_1519ef90_oracle import sqrt_word
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments import game_side_ring_emitter_1519f7f0_recovery as source
R,O,ENTRY=source.ROOT,source.OUT,source.ENTRY
E,P,A,S,T,ALT,CREATED=0x30000,0x50000,0x60000,0x70000,0x71000,0x72000,0x74000
SIDE,CLEAN,FACTORY,RNG,FLOOR,COPY=0x1519EF90,0x1519F48C,0x151491F4,0x150ADA20,0x15045800,0x10022EC0
s8=lambda n:((n&255)^128)-128
s16=lambda n:((n&65535)^32768)-32768
@lru_cache(None)
def symbols():return {x[1]:x[2][1] for x in symbol_rows((R/'conker/build/conker.us.elf').read_bytes())}
@dataclass(frozen=True)
class Case:
 cap:int=5;head:int=0;tail:int=4;count:int=4;flags:int=4;gate:int=0;mode:int=6
 hit:int=1;factory:int=1;motion:int=0;progress:int=0x3E800000;scale:int=0x3F000000
 random:int=0xFFFFFFFF;side_effects:int=0;rng_effects:int=0;floor_effects:int=0;floor_hit:int=1
 phase:int=0;rule:str='left';height:int=0xC6147000;seed:int=0
 bound:int=0x469C4000
def fixture(c):
 m={STACK+c.phase+i:(i*17+c.seed*19+0xA5)&255 for i in range(-1024,1024)}
 for at,n in ((E,160),(P,80),(A,36*c.cap),(S,128),(T,0x200),(ALT,512),(CREATED,128)):
  assert at+n<=STACK+c.phase-1024 or at>=STACK+c.phase+1024
  for i in range(n):m[at+i]=(i*13+c.seed*7+0x53)&255
 put(m,E+0x94,A);put(m,E+0x98,P);put(m,P,S);put(m,S+0x18,T)
 put(m,T,0 if c.gate==1 else 1);put(m,T+0x1D4,0 if c.gate==2 else 0x12345678)
 m[S+0x1C]=7;m[T+0x3B]=8 if c.gate==3 else 7
 for off,v in ((0x14,3.),(0x18,12.5),(0x1C,4.)):put(m,T+off,bits(v))
 put(m,T+0x118,c.height)
 put(m,E+0x1E,c.flags,2);put(m,E+0x20,c.mode)
 for off,v in ((0x25,c.cap),(0x2C,c.count),(0x2D,c.head),(0x2E,c.tail)):m[E+off]=v&255
 for off,v in ((8,c.scale),(12,c.progress),(28,bits(.75)),(56,bits(.5)),(60,bits(2.)),(76,bits(1.5))):put(m,P+off,v)
 for off,v in ((0x28,0x7FFF),(0x2E,100),(0x30,255),(0x32,3)):put(m,P+off,v,2)
 m[P+0x44]=3;m[P+0x45]=7
 for off in (16,20,24):put(m,P+off,0)
 put(m,symbols()['D_800BE9A4'],bits(.5))
 for key,v in (('D_800A8CF4',0x38D1B717),('D_800A8CF8',c.bound),('D_800A8CFC',bits(-9500.))):put(m,symbols()[key],v)
 return m
def public(m,c):return {a:v for a,v in m.items() if not STACK+c.phase-1024<=a<STACK+c.phase+1024}
def side(m,c,args,ordinal):
 packet,mode,out=args
 coords=((3.,4.,0.),(0.,0.,0.),(20001.,0.,0.),(-3.,0.,-4.),(.00001,0.,0.))
 for i,v in enumerate(coords[c.motion]):put(m,out+4*i,bits(v))
 if c.side_effects&1:
  put(m,packet,ALT);put(m,S+0x18,ALT+0x100)
  for off,v in ((0x14,20.),(0x18,21.),(0x1C,-30.)):put(m,T+off,bits(v))
 if c.side_effects&2:put(m,E+0x94,ALT);put(m,E+0x98,ALT+0x100)
 if c.side_effects&4:put(m,E+0x20,7);put(m,E+0x1E,0x82,2)
 return c.hit
def clean(m,c,args):
 # An opaque ABI provider retains a valid owner. Actual cleanup is audited
 # separately; it clears packet.state and leads to the retail low-address store.
 put(m,P,ALT if c.side_effects&8 else S)
 m[E+0x30]=0;put(m,E+0x1E,read(m,E+0x1E,2)&~2,2);m[P+4]|=1
def factory(m,c,args):
 assert args==(300,0xFFFFFFFF,11,0,6,8,255,0),args
 if c.side_effects&16:put(m,E+0x20,7);put(m,P,ALT)
 return CREATED if c.factory else 0
def rng(m,c,ordinal):
 if c.rng_effects&1:
  put(m,P+0x28,0x8001,2);m[P+0x44]=255;m[P+0x45]=255
 if c.rng_effects&2:
  at=A+36*s8(m[E+0x2E]);put(m,at+28,bits(-.25));put(m,at+32,bits(.75))
 if c.rng_effects&4:put(m,T+0x118,bits(-9600.));put(m,T+0x18,bits(50.))
 return c.random
def floor(m,c,ordinal,args):
 point,zero,bottom,out=args
 for i in range(36):m[out+i]=(ordinal*31+i*7+0xA5)&255
 put(m,out,bits(20.25+ordinal))
 if c.floor_effects&1:put(m,P+12,bits(1.25) if ordinal==0 else bits(0.))
 if c.floor_effects&2:put(m,symbols()['D_800A8CF8'],0);put(m,symbols()['D_800BE9A4'],bits(10.))
 if c.floor_effects&4:m[E+0x2D]=(m[E+0x2D]+1)%c.cap;m[E+0x2C]=1
 for i in range(12):m[point+i]^=0x5A
 return c.floor_hit if c.floor_hit in (0,1) else ordinal&1
def reference(initial,c,transition_offset=-44,point_offset=-140,side_provider=side):
 m=initial.copy();p=read(m,E+0x98);a=read(m,E+0x94);state=read(m,p);actor=read(m,state+0x18);calls=[];ops=[]
 def op(x,y,k):ops.append((k,x,y));return fp(x,y,k,c.rule)
 def absolute(x):ops.append(('abs',x));return x&0x7FFFFFFF
 def less(x,y):ops.append(('lt',x,y));return floating(x)<floating(y)
 def negative(x):ops.append(('neg',x));return x^0x80000000
 if not read(m,actor) or not read(m,actor+0x1D4) or m[state+0x1C]!=m[actor+0x3B]:return m,0,calls,ops
 initialized=False
 def query():
  args=(p,read(m,E+0x20)&255,E+16);calls.append((SIDE,args));return side_provider(m,c,args,0)
 if not read(m,E+0x1E,2)&4:
  if not query():return m,1,calls,ops
  for off in (0,4,8):put(m,p+16+off,read(m,E+16+off))
  put(m,E+0x1E,read(m,E+0x1E,2)|4,2);initialized=True
 if not initialized and not query():
  calls.append((CLEAN,(E,)));clean(m,c,(E,));state=read(m,p);outputs=state+0x58
  transition=STACK+c.phase+transition_offset;put(m,transition,state);m[transition+4]=read(m,E+0x20)&255
  args=(300,0xFFFFFFFF,11,0,6,8,255,0);calls.append((FACTORY,args));created=factory(m,c,args)
  if created:
   data=bytes(m[transition+i] for i in range(8));calls.append((COPY,(created+0x28,8),data))
   for i,v in enumerate(data):m[created+0x28+i]=v
  put(m,outputs+(4 if read(m,E+0x20)==6 else 12),created)
  return m,1,calls,ops
 put(m,p+32,read(m,actor+20));put(m,p+36,read(m,actor+28))
 dx,dy,dz=[op(read(m,E+16+off),read(m,p+16+off),'sub') for off in (0,4,8)]
 limit=read(m,symbols()['D_800A8CF4'])
 if less(limit,absolute(dx)) or less(limit,absolute(dy)) or less(limit,absolute(dz)):
  length2=op(op(op(dx,dx,'mul'),op(dy,dy,'mul'),'add'),op(dz,dz,'mul'),'add')
  ops.append(('sqrt',length2));length=sqrt_word(length2);inverse=op(bits(1.),length,'div')
  put(m,p+12,op(read(m,p+12),op(length,read(m,p+8),'mul'),'add'))
 if not less(bits(1.),read(m,p+12)):return m,1,calls,ops
 assert 'inverse' in locals(),'Invalid retained-progress/no-motion state has undefined private input'
 fraction=op(bits(1.),read(m,p+12),'div');remaining=op(read(m,p+28),read(m,symbols()['D_800BE9A4']),'add')
 time_step=op(remaining,fraction,'mul');position=[read(m,p+16+i*4) for i in range(3)]
 weight=op(read(m,p+56),op(read(m,p+60),remaining,'mul'),'add');weight_step=op(read(m,p+56),weight,'sub')
 if read(m,E+32)==7:velocity=[op(op(negative(dz),inverse,'mul'),read(m,p+76),'mul'),op(op(dx,inverse,'mul'),read(m,p+76),'mul')]
 else:velocity=[op(op(dz,inverse,'mul'),read(m,p+76),'mul'),op(op(negative(dx),inverse,'mul'),read(m,p+76),'mul')]
 previous=s8(m[E+0x2E])-1
 if previous<0:previous=m[E+0x25]-1
 if previous!=s8(m[E+0x2D]) and s8(m[E+0x2C])!=0:
  previous-=1
  if previous<0:previous=m[E+0x25]-1
  for off,v in zip((28,32),velocity):put(m,a+36*previous+off,op(op(read(m,a+36*previous+off),v,'add'),bits(.5),'mul'))
 steps=[op(v,fraction,'mul') for v in (dx,dy,dz)];weight_step=op(weight_step,fraction,'mul');bound=read(m,symbols()['D_800A8CF8']);n=0
 while True:
  assert n<100,'Reference iteration budget exceeded';at=a+36*s8(m[E+0x2E])
  for off,v in zip((28,32),velocity):put(m,at+off,v)
  put(m,at,position[0]);put(m,at+4,position[2]);put(m,at+24,read(m,p+46,2),2);put(m,at+12,weight)
  for off,src in ((16,48),(18,50),(22,40)):put(m,at+off,read(m,p+src,2),2)
  put(m,at+20,255,2);calls.append((RNG,()));random=rng(m,c,n)
  put(m,p+40,s16(read(m,p+40,2))+m[p+68]+(random%(m[p+69]+1)),2)
  for off,v in ((0,28),(4,32)):put(m,at+off,op(read(m,at+off),op(read(m,at+v),remaining,'mul'),'add'))
  point=STACK+c.phase+point_offset;put(m,point,read(m,at));height=read(m,actor+0x118)
  if less(height,read(m,symbols()['D_800A8CFC'])):height=read(m,actor+24)
  put(m,point+4,op(height,bits(100.),'add'));put(m,point+8,read(m,at+4));accepted=True
  if less(bound,absolute(read(m,point))) or less(bound,absolute(read(m,point+8))):accepted=False
  else:
   bottom=op(read(m,point+4),bits(200.),'sub');args=(point,0,bottom,E+0x60)
   calls.append((FLOOR,(0,bottom,E+0x60),bytes(m[point+i] for i in range(12))))
   ordinal=sum(x[0]==FLOOR for x in calls)-1
   if floor(m,c,ordinal,args):put(m,at+8,read(m,E+0x60))
   else:accepted=False
  if accepted:
   m[E+0x2E]=(s8(m[E+0x2E])+1)&255
   if s8(m[E+0x2E])==m[E+0x25]:m[E+0x2E]=0
   m[E+0x2C]=(s8(m[E+0x2C])+1)&255
   if s8(m[E+0x2D])==s8(m[E+0x2E]):
    m[E+0x2D]=(s8(m[E+0x2D])+1)&255
    if s8(m[E+0x2D])==m[E+0x25]:m[E+0x2D]=0
    m[E+0x2C]=(s8(m[E+0x2C])-1)&255
  position=[op(x,y,'add') for x,y in zip(position,steps)];weight=op(weight,weight_step,'add');remaining=op(remaining,time_step,'sub')
  put(m,p+12,op(read(m,p+12),bits(1.),'sub'));n+=1
  if not less(bits(1.),read(m,p+12)):break
 for i,v in enumerate(position):put(m,p+16+4*i,v)
 put(m,p+28,remaining);return m,1,calls,ops
class Machine(FactoryOracle):
 def __init__(self,w,m,c,connected=None):
  self.c=c;self.fp_ops=[];self.raw_calls=[]
  super().__init__(w,m,BaseCase(phase=c.phase),entry=ENTRY,s={},arguments=(E,),connected=connected)
 def execute(self,w):
  op,fmt,fn=w>>26,w>>21&31,w&63
  if op==0 and fn==3:
   v=self.r[w>>16&31];self.r[w>>11&31]=((v if v<0x80000000 else v-0x100000000)>>(w>>6&31))&0xFFFFFFFF;return
  if op==17 and fmt==16 and fn in (0,1,2,3,4,5,7,60):
   fs,ft,fd=w>>11&31,w>>16&31,w>>6&31;x,y=self.f[fs],self.f[ft]
   if fn<4:
    k=('add','sub','mul','div')[fn];self.fp_ops.append((k,x,y));self.f[fd]=fp(x,y,k,self.c.rule)
   elif fn==4:self.fp_ops.append(('sqrt',x));self.f[fd]=sqrt_word(x)
   elif fn==5:self.fp_ops.append(('abs',x));self.f[fd]=x&0x7FFFFFFF
   elif fn==7:self.fp_ops.append(('neg',x));self.f[fd]=x^0x80000000
   else:self.fp_ops.append(('lt',x,y));self.condition=floating(x)<floating(y)
   return
  return super().execute(w)
 def record_call(self,t):
  n={SIDE:3,CLEAN:1,FACTORY:8,RNG:0,FLOOR:4,COPY:3}[t];a=tuple(self.arguments(n));self.raw_calls.append((t,a))
  if t==FLOOR:self.calls.append((t,a[1:],bytes(self.memory[a[0]+i] for i in range(12))))
  elif t==COPY:self.calls.append((t,(a[0],a[2]),bytes(self.memory[a[1]+i] for i in range(a[2]))))
  else:self.calls.append((t,a))
 def hook(self,t):
  a=self.raw_calls[-1][1];ordinal=sum(x[0]==t for x in self.raw_calls)-1
  if t==SIDE:value=side(self.memory,self.c,a,ordinal)
  elif t==CLEAN:clean(self.memory,self.c,a);value=0
  elif t==FACTORY:value=factory(self.memory,self.c,a)
  elif t==RNG:value=rng(self.memory,self.c,ordinal)
  elif t==FLOOR:value=floor(self.memory,self.c,ordinal,a)
  else:
   data=bytes(self.memory[a[1]+i] for i in range(a[2]))
   for i,v in enumerate(data):self.memory[a[0]+i]=v
   value=a[0]
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi=self.lo=0xDEADBEEF;self.r[2]=value&0xFFFFFFFF
def programs():
 return dict(retail=list(struct.unpack_from('>415I',(R/'conker/conker.us.bin').read_bytes(),0x1CCCA0)),previous=bound_blob(*payload(O/'previous.o','func_1519F7F0'),symbols()),candidate=bound_blob(*payload(O/'qualified.o','func_1519F7F0'),symbols()))
def check(w,c,label):
 m=fixture(c);expected,value,calls,ops=reference(m,c,-48 if label=='previous' else -44,-128 if label=='previous' else -140)
 q=Machine(w,m,c).run();got=(public(q.memory,c),q.r[2],q.calls);want=(public(expected,c),value,calls)
 assert got==want,(label,c,'memory',[(hex(k),expected.get(k),q.memory.get(k)) for k in expected if public(expected,c).get(k)!=public(q.memory,c).get(k)][:8],'return',q.r[2],value,'calls',q.calls,calls)
 return q
def cases():
 # The first emission is out of bounds, but the next enters the query box.
 # Query callback ordinals must count calls rather than emission iterations.
 yield Case(bound=bits(1.1))
 for flags,gate,hit,mode,factory_out in itertools.product((0,4),range(4),(0,1),(6,7,0x106),(0,1)):
  yield Case(flags=flags,gate=gate,hit=hit,mode=mode,factory=factory_out)
 for cap in (1,2,5):
  for head,tail,count,motion,hit,mode in itertools.product((0,cap-1),(0,cap-1),(0,cap),(0,1,2,3,4),(0,1,2),(6,7)):
   if (head+tail+count+motion+hit+mode)%3:continue
   yield Case(cap=cap,head=head,tail=tail,count=count,motion=motion,floor_hit=hit,mode=mode,scale=bits(.0001) if motion==2 else bits(.5))
 for side_e,rng_e,floor_e,random in itertools.product((0,1,2,4,7),(0,1,2,4,7),(0,1,2,4,7),(0,0x80000000,0xFFFFFFFF)):
  if (side_e+rng_e+floor_e+random)%7:continue
  yield Case(side_effects=side_e,rng_effects=rng_e,floor_effects=floor_e,random=random)
 for side_e,factory_out,phase,seed in itertools.product((0,8,16,24),(0,1),(0,8),(0,1,2)):
  yield Case(hit=0,side_effects=side_e,factory=factory_out,phase=phase,seed=seed)
 for height,bound,mode,count in itertools.product((bits(-9600.),bits(-9500.),bits(-9400.)),(0,bits(.25),bits(20000.)),(6,7),(-128,-1,0,127)):
  yield Case(height=height,bound=bound,mode=mode,count=count)
 for progress,scale,motion,rule in itertools.product((0,0x80000000,bits(1.),bits(-1.),0x7FC12345),(0,bits(.5),0x7FC30002),(0,1),('left','right')):
  yield Case(progress=progress,scale=scale,motion=motion,rule=rule)
def controls(streams):
 rejected=[]
 for name,word,mask,c in (
  ('gate-byte',0x9299003B,1,Case()),
  ('unsigned-random',0x004C001B,1,Case(random=0xFFFFFFFF)),
  ('duration-field',0x866D002E,2,Case()),
  ('floor-span',0x3C014348,1,Case()),
  ('retained-padding',0x27A500EC,4,Case(hit=0)),
  ('tail-cursor',0x8239002E,1,Case()),
 ):
  w=streams['retail'][:];assert w.count(word)==1,(name,w.count(word));w[w.index(word)]^=mask
  try:check(w,c,'retail')
  except (AssertionError,KeyError):rejected.append(name)
  else:raise AssertionError(('ineffective control',name))
 return rejected
def qualify_match(streams,out):
 seen={k:set() for k in streams};count=0
 for c in cases():
  machines={label:check(w,c,label) for label,w in streams.items()}
  retail=machines['retail']
  for label,q in machines.items():
   assert (q.fp_ops,q.raw_calls,q.calls)==(retail.fp_ops,retail.raw_calls,retail.calls),('ordered FP/provider arguments',label,c)
   seen[label]|=q.visits
  count+=1
 report=dict(cases_per_stream=count,streams=len(streams),visited_words={k:len(v) for k,v in seen.items()},ordered_FP_operations_and_raw_provider_arguments_equal=True,all_eight_transition_bytes_equal=True,effective_controls=controls(streams),injected_literal_values_instruction_only=True,c_match_credit=0)
 (out/'guest-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)

def main():
 streams=programs();seen={k:set() for k in streams};count=0;different_previous_packets=0;different_candidate_packets=0;fp_examples=[]
 for c in cases():
  observations={};machines={}
  for label,w in streams.items():
   q=check(w,c,label);seen[label]|=q.visits;observations[label]=[x[2] for x in q.calls if x[0]==COPY];machines[label]=q
  different_previous_packets+=observations['retail']!=observations['previous']
  different_candidate_packets+=observations['retail']!=observations['candidate']
  a,b=machines['retail'],machines['candidate']
  assert (public(a.memory,c),a.calls,a.raw_calls)==(public(b.memory,c),b.calls,b.raw_calls),('refined public/calls',c)
  if a.fp_ops!=b.fp_ops and len(fp_examples)<3:
   first=next((i for i,(x,y) in enumerate(zip(a.fp_ops,b.fp_ops)) if x!=y),min(len(a.fp_ops),len(b.fp_ops)))
   fp_examples.append(dict(case=repr(c),first=first,retail=a.fp_ops[max(0,first-1):first+3],candidate=b.fp_ops[max(0,first-1):first+3]))
  count+=1
 assert different_previous_packets>0 and different_candidate_packets==0,'Exposed-home provenance control failed'
 rejected=controls(streams)
 report=dict(cases_per_stream=count,streams=3,visited_words={k:len(v) for k,v in seen.items()},all_eight_transition_bytes_and_provider_arguments_equal=True,
             previous_transition_packet_disagreements=different_previous_packets,transition_packet_disagreements=different_candidate_packets,
             ordered_FP_equivalence_proved=False,remaining_FP_order_examples=fp_examples,effective_controls=rejected,c_match_credit=0)
 (O/'guest-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
