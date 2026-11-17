"""Independent region-emitter reference and bounded original/raw executions."""
from tools.experiments import game_region_emitter_151a5660_recovery as source
from dataclasses import dataclass,asdict,replace
from collections import Counter
from pathlib import Path
import hashlib,itertools,json,math,struct,sys
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_quaternion_matrix_1504a140_oracle import fp
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests import game_radial_effect_150c29f0_oracle as trig_source
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
R=source.ROOT;O=source.OUT;ENTRY=source.ENTRY
E,A,B,MASK,MARK=0x30000,0x50000,0x60000,0x70000,0x70010
RNG,REAL,TRIG,HEIGHT,EMIT,VIEW=0x150ADA20,0x150ADA68,0x151423D8,0x15046C80,0x15149550,0x151464B8
DT,COEF,TABLE=0x800BE9A4,0x800A8D80,0x8009A220
COEFFICIENTS=(0x3F360B61,0x41B4CCCD,0x415C9375,0x4267E042,0x422ADB23,0x42ED86A8)
u32=lambda v:v&0xffffffff
half=lambda v:((v&65535)^32768)-32768
data=lambda m,p,n:bytes(m[p+i]for i in range(n))
public=lambda m:{p:v for p,v in m.items()if not STACK-4096<=p<STACK+1024}
def packet(m,p):return bytes(0 if 0x35<=i<0x38 else m[p+i]for i in range(72))
@dataclass(frozen=True)
class Case:
 seed:int=0;mode:int=0;route:int=0;query:int=0;hit:int=0;pattern:int=0;mutation:int=0;phase:int=0;alias:int=0;angle:int=0x42B40000;native:int=1
def cases():
 for mode,angle in itertools.product((0,1),range(256)):
  yield Case(seed=angle,mode=mode,query=angle&1,hit=angle>>1&1,pattern=angle%8,phase=(angle&1)*8)
 for mode,route,query,hit,pattern in itertools.product(range(4),range(5),(0,1),(0,1),range(8)):
  if (mode+route+query+hit+pattern)%5:continue
  yield Case(seed=pattern*41+route,mode=mode|0xAC,route=route,query=query,hit=hit,pattern=pattern,phase=query*8)
 for mode,mutation,pattern in itertools.product(range(4),(1,2,4,8,16,31),range(4)):
  yield Case(seed=mode*37+mutation,mode=mode,query=1,hit=pattern&1,pattern=pattern+4,mutation=mutation,phase=(pattern&1)*8)
 for angle,query,mutation in itertools.product((0.,1.,89.5,180.,359.,3.1e9,6.0e9),(0,1),(0,2)):
  yield Case(seed=73,mode=2,query=query,hit=1,pattern=6,mutation=mutation,angle=bits(angle))
 for mode,mutation in itertools.product(range(4),(0,2,4,8,16,31)):
  yield Case(seed=17,mode=mode,query=1,hit=1,pattern=6,mutation=mutation,alias=1,native=0)
 for angle in(0xBF800000,0xCF000000,0x7FC00001,0x7F800000,0xFF800000):
  yield Case(seed=19,mode=2,query=1,hit=1,pattern=4,angle=angle,native=0)
def fixture(c):
 m={STACK+i:(i*17+c.seed*13+0xA5)&255 for i in range(-4096,1024)}
 for at,n in((E,512),(A,24),(B,24),(MASK,4),(MARK,4),(DT,4),(COEF,24),(TABLE,260)):
  m.update({at+i:(i*29+c.seed*11+0x5A)&255 for i in range(n)})
 for at,k in((A,0),(B,1),(E,0))if c.alias else((A,0),(B,1)):
  xyz=((-32768,32767,-32768),(17,-91,255),(32767,-32768,0),(0,0,0))[c.pattern%4]
  for off,v in zip((0,2,4,6,8,10),(*xyz,(-32768,-1,0,32767)[c.pattern%4],(32767,0,-32768,7)[c.pattern%4],(-32768,9,0,32767)[c.pattern%4])):put(m,at+off,v,2)
  put(m,at+16,c.angle);m[at+20]=1 if c.route==2 and not k else 0;m[at+21]=c.mode^(k&1)
 m[E+1]=(c.seed*7)&255;m[E+12]=c.seed&255;m[E+13]=0;put(m,E+14,0xFF81,2)
 put(m,E+40,0 if c.route==1 else E if c.alias else A)
 for off,value in((4,(.5,0.,-1.,1.)[c.pattern%4]),(8,(1.,2.,0.,.25)[c.pattern%4]),(12,(0.,1.,1.0000001192092896,2.,3.75,.5,4.5,-2.)[c.pattern]),(16,1.125),(20,-2.),(24,3.),(28,.5),(32,1.25),(40,2.5),(44,-.75),(48,-3.),(52,1.5),(56,.25),(60,2.)):
  put(m,E+40+off,bits(value))
 put(m,E+40+36,(-32768,-1,0,32767)[c.pattern%4],2);put(m,E+40+38,(-32768,0,32767,1)[c.pattern%4],2)
 m[E+40+64]=c.query;m[E+40+65]=(c.seed*3)&255;m[E+40+66]=(0,1,127,255)[c.pattern%4]
 put(m,E+40+108,MASK if c.route in(3,4)else 0);put(m,DT,bits((1.,0.,2.,-.5)[c.pattern%4]))
 for i,v in enumerate(COEFFICIENTS):put(m,COEF+4*i,v)
 for i,v in enumerate(trig_source.quarter()):put(m,TABLE+4*i,v)
 return m
class Service:
 def __init__(self,m,c,home):self.m=m;self.c=c;self.home=home;self.counts=Counter();self.calls=[];self.packet_at=None;self.query_at=None
 def invoke(self,target,args):
  m,c=self.m,self.c;ordinal=len(self.calls);local=self.counts[target];self.counts[target]+=1
  observed=b'';normal=list(args)
  if target==HEIGHT:
   observed=data(m,args[0],12);self.query_at=args[0];normal[0]='query'
  elif target==EMIT:
   observed=packet(m,args[0]);self.packet_at=args[0];normal[0]='packet'
  self.calls.append((target,tuple(normal),observed))
  if target==TRIG:return trig_source.trig(args[0])
  put(m,MARK,u32(0x13579BDF+ordinal*0x10203+target))
  if target==VIEW:answer=1 if c.route==3 else 0
  elif target==RNG:answer=u32((c.seed<<24)^(local*0x9E3779B9)^(0,1,0x7fffffff,0x80000000,0xffffffff)[(local+c.pattern)%5])
  elif target==REAL:answer=bits((0.,.25,.5,.75,1.,-.5)[(local+c.pattern+c.seed)%6])
  elif target==HEIGHT:
   for i in range(36):m[args[3]+i]=(i*13+ordinal*7+c.seed)&255
   put(m,args[3],bits((c.seed-100)*.125+local*.5));answer=c.hit^((local&1)if c.mutation&8 else 0)
  else:assert target==EMIT;answer=0xE5000002
  if c.mutation&1 and target==EMIT and local==0:put(m,E+52,bits(4.5))
  if c.mutation&2 and target in(RNG,REAL):
   put(m,E+40,B if (ordinal+c.seed)&1 else E if c.alias else A)
   m[E+104]^=1
  if c.mutation&4:
   m[E+12]^=(0x37+ordinal)&255;m[E+1]^=(0x65+ordinal)&255
   put(m,E+60,bits((ordinal%7)-2.));put(m,E+64,bits((ordinal%5)*.25))
   put(m,E+68,bits((ordinal%3)*.5));put(m,E+72,bits((ordinal%5)*.125))
   put(m,E+80,bits((ordinal%3)-1.));put(m,E+88,bits((ordinal%7)*.25));put(m,E+96,bits((ordinal%3)*.5))
   m[E+105]^=0x55;m[E+106]=(ordinal*17)&255
  if c.mutation&8:
   p=read(m,E+40)
   if p:
    for off in(0,2,4,6,8,10):put(m,p+off,half(c.seed*37+off*19+ordinal*11),2)
   put(m,DT,bits((ordinal%3)*.5))
  if c.mutation&16:
   if self.packet_at is not None:
    for i in range(72):
     if not 0x35<=i<0x38:m[self.packet_at+i]^=0x3C
   if self.query_at is not None:
    for i in range(12):m[self.query_at+i]^=0xA5
  return answer
def reference(initial,c,home=None):
 m=dict(initial);home=STACK+c.phase if home is None else home;p=home-76;q=home-156;s=E+40;service=Service(m,c,home)
 f=lambda at:read(m,at);h=lambda at:half(read(m,at,2));cvt=lambda v:bits(float(v));op=lambda k,a,b:fp(a,b,k,'left')
 mul=lambda a,b:op('mul',a,b);add=lambda a,b:op('add',a,b);sub=lambda a,b:op('sub',a,b)
 call=service.invoke;source=lambda:read(m,s)
 if not source():put(m,E+14,-1,2);return m,service.calls
 if m[source()+20]==1:return m,service.calls
 if read(m,s+108)and call(VIEW,(read(m,s+108),)):return m,service.calls
 put(m,s+12,add(f(s+12),mul(mul(f(s+8),f(s+4)),f(DT))))
 if not 1.<floating(f(s+12)):return m,service.calls
 for off,v,n in((32,0x6231,2),(34,0x1A4D,2),(38,0,1),(39,0,1),(40,0,1),(41,255,1),(42,1,2),(45,255,1),(48,0,4),(46,0,1),(47,0,1),(52,16,1),(60,f(s+16),4)):put(m,p+off,v,n)
 emissions=0
 while True:
  emissions+=1;assert emissions<=10,('unbounded fixture',c)
  mode=m[source()+21]&3
  if mode==3:
   put(m,p,cvt(h(source())));put(m,p+8,cvt(h(source()+4)));a=h(source()+2);b=h(source()+8);lower=cvt(a-b);upper=cvt(a+b)
  else:
   if mode==2:
    product=floating(mul(f(source()+16),f(COEF)))
    value=math.trunc(product)if math.isfinite(product)else -1
    angle=(value if 0<=value<0x100000000 else -1)&255
   else:angle=call(RNG,())&255
   cosine=call(TRIG,((angle-64)&255,));sine=call(TRIG,(angle,))
   a=call(REAL,());radius=h(source()+6)
   if mode==2:
    first=add(mul(a,add(cvt(radius),cvt(radius))),cvt(-radius))
    b=call(REAL,());radius=h(source()+10);second=add(mul(b,add(cvt(radius),cvt(radius))),cvt(-radius))
    x=add(cvt(h(source())),add(mul(first,sine),mul(second,cosine)))
    put(m,p,x);put(m,p+8,add(cvt(h(source()+4)),sub(mul(second,sine),mul(first,cosine))))
   else:
    radius=mul(a,cvt(radius));put(m,p,add(cvt(h(source())),mul(radius,sine)));put(m,p+8,sub(cvt(h(source()+4)),mul(radius,cosine)))
   a=h(source()+2);b=h(source()+8)
   if mode==0:lower=cvt(a);upper=cvt(a+b)
   else:upper=cvt(a+b);lower=cvt(a-b)
  if m[s+64]:
   for off,v in((0,f(p)),(4,upper),(8,f(p+8))):put(m,q+off,v)
   accepted=call(HEIGHT,(q,0,lower,s+72));put(m,p+4,f(s+72)if accepted else lower)
  else:put(m,p+4,lower)
  horizontal=call(REAL,());horizontal=add(mul(horizontal,f(s+24)),f(s+20))
  vertical=call(REAL,());vertical=add(mul(vertical,f(s+32)),f(s+28))
  for off,at,scale in((12,4,horizontal),(20,8,horizontal),(16,12,vertical),(24,16,vertical),(28,20,vertical)):put(m,p+off,mul(f(COEF+at),scale))
  value=call(RNG,());divisor=u32(h(s+38)+1);assert divisor;put(m,p+36,value%divisor+h(s+36),2)
  for off,base,span in((56,40,44),(64,48,52),(68,56,60)):
   value=call(REAL,());put(m,p+off,add(mul(value,f(s+span)),f(s+base)))
  value=call(RNG,());put(m,p+44,value%(m[s+66]+1)+m[s+65],1)
  call(EMIT,(p,10,0,0,m[E+12],m[E+1]));put(m,s+12,sub(f(s+12),bits(1.)))
  if not 1.<floating(f(s+12)):break
 return m,service.calls
class Oracle(FactoryOracle):
 def __init__(self,w,initial,c):
  super().__init__(w,initial,c,entry=ENTRY,arguments=(E,),s={},connected=trig_source.helper_code())
  self.service=Service(self.memory,c,self.target_home);self.fcsr=0;self.conversions=Counter();self.before_f=self.f[:]
 def execute(self,w):
  op,fmt,ft,fs,fd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
  if op==17:
   if fmt==2:assert fs==31;self.r[ft]=self.fcsr;return
   if fmt==6:assert fs==31;self.fcsr=self.r[ft];return
   if fmt==20 and fn==32:self.f[fd]=bits(float((self.f[fs]^0x80000000)-0x80000000));return
   if fmt==16:
    x,y=self.f[fs],self.f[ft]
    if fn in(0,1,2,3):self.f[fd]=fp(x,y,('add','sub','mul','div')[fn],'left');return
    if fn==6:self.f[fd]=x;return
    if fn==7:self.f[fd]=x^0x80000000;return
    if fn==60:self.condition=floating(x)<floating(y);return
    if fn==36:
     value=floating(x);integer=math.trunc(value)if math.isfinite(value)else -0x80000001
     valid=-0x80000000<=integer<=0x7fffffff;self.conversions['valid'if valid else'invalid']+=1
     self.f[fd]=u32(integer)if valid else 0x80000000
     self.fcsr=(self.fcsr&3)|(0 if valid else 0x40);return
  return super().execute(w)
 def record_call(self,t):
  assert t in(RNG,REAL,TRIG,HEIGHT,EMIT,VIEW),hex(t)
  count={RNG:0,REAL:0,TRIG:1,HEIGHT:4,EMIT:6,VIEW:1}[t];args=tuple(self.arguments(count));self.pending=(t,args)
  if t==TRIG:self.service.invoke(t,args)
 def hook(self,t):
  target,args=self.pending;assert target==t and t!=TRIG
  answer=self.service.invoke(t,args)
  count=6 if t==EMIT else 4
  for i in range(count):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi=self.lo=0xDEADBEEF;self.r[2]=answer
  if t==REAL:self.f[0]=answer
def programs():return source.programs()
def verify(w,c):
 initial=fixture(c);expected,calls=reference(initial,c);m=Oracle(w,initial,c).run()
 got=public(m.memory);want=public(expected)
 assert got==want,('public memory',c,[(hex(p),want.get(p),got.get(p))for p in want if want.get(p)!=got.get(p)][:8])
 assert m.service.calls==calls,('call mismatch',c,next(((i,a,b)for i,(a,b)in enumerate(zip(m.service.calls,calls))if a!=b),None),len(m.service.calls),len(calls))
 assert m.f[20:]==m.before_f[20:]
 return m
def main():
 dest=O/'finite-guest-v39-rev2.json';assert not dest.exists();code=programs();seen={k:set()for k in code};counts=Counter();conversions=Counter();n=0
 for c in cases():
  for label,w in code.items():
   machine=verify(w,c);seen[label].update(machine.visits);conversions.update(machine.conversions)
  counts['native_eligible'if c.native else'guest_only']+=1;n+=1
 controls=[]
 for name,off,old,new,c in [('expiry-width',0x44,0xA64F000E,0xAE4F000E,Case(route=1)),('disabled-byte',0x50,0x93190014,0x93190015,Case(route=2)),('byte-code',0x98,0x24086231,0x24086230,Case(pattern=4)),('loop-subtract',0x604,0x461C3481,0x461C3480,Case(pattern=4)),('outer-fallback',0x4B8,0xE7B400C0,0xE7B400C4,Case(pattern=4))]:
  bad=code['retail'][:];assert bad[off//4]==old,(name,hex(bad[off//4]));bad[off//4]=new
  try:verify(bad,c)
  except(AssertionError,KeyError):controls.append(name)
  else:raise AssertionError(('ineffective finite control',name))
 report=dict(cases=n,case_kinds=dict(counts),streams=list(code),conversion_counts=dict(conversions),target_words_visited={k:len(v&set(range(ENTRY,ENTRY+1612,4)))for k,v in seen.items()},trig_words_visited={k:len(v&set(trig_source.helper_code()))for k,v in seen.items()},controls=controls,packet_defined_bytes=69,packet_padding_bytes_uncredited=3,source_installed=source.installed(),c_match_credit=0,physical_FCSR_or_fault_state_not_claimed=True)
 dest.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
