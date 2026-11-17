"""Independent bounded ground-link reference; unwritten packet holes get no credit."""
from pathlib import Path
from dataclasses import dataclass,asdict
import json,struct,itertools
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.game_quaternion_matrix_1504a140_oracle import fp
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments import game_ground_link_151aadf8_recovery as source
R,P,ENTRY=source.ROOT,source.OUT,source.ENTRY
OWNER,ACTOR,OUTPUT,MARK,TABLE,COEF=0x30000,0x40000,0x50000,0x70000,0x800AB414,0x800A8FE0
QUERY,SELECT,FLOAT,INT,CREATE=0x15045800,0x151D8E20,0x150ADA68,0x150ADA20,0x1513C73C
SYMS={r[1]:r[2][1]for r in symbol_rows((R/'conker/build/conker.us.elf').read_bytes())};COPY=SYMS['memcpy']
COUNTS={QUERY:4,SELECT:0,FLOAT:0,INT:0,CREATE:14,COPY:3};PHOLES=(5,6,7,26,27);DHOLES=(7,)
u32=lambda n:n&0xffffffff
data=lambda m,p,n:bytes(m[p+i]for i in range(n))
def masked(m,p,n,holes):return bytes(0 if i in holes else m[p+i]for i in range(n))
@dataclass(frozen=True)
class Case:
 seed:int=0;route:int=3;mutation:int=0;phase:int=0
def cases():
 for seed,route in itertools.product(range(256),range(4)):yield Case(seed,route,seed%32,(seed&1)*8)
 for seed,mutation,phase in itertools.product((0,1,2,6,12),(0,1,2,4,8,16,31),(0,8)):yield Case(seed,3,mutation,phase)
def fixture(c):
 m={STACK+i:(i*17+c.seed*13+0xA5)&255 for i in range(-4096,1024)}
 for at,n in((OWNER,512),(ACTOR,512),(OUTPUT,512),(MARK,4),(TABLE,768),(COEF,12)):m.update({at+i:(i*29+c.seed*11+0x5a)&255 for i in range(n)})
 put(m,OWNER+0x18,ACTOR);put(m,OWNER+0x70,OUTPUT if c.route==0 else 0)
 for off,v in((0x14,bits((c.seed-128)*.25)),(0x18,bits((c.seed-100)*.5)),(0x1c,bits((c.seed-60)*-.125)),(0x118,(bits(-9600.),bits(-9500.),bits(-9400.),0x7fc00001,0x80000000,0x7f800000)[c.seed%6])):put(m,ACTOR+off,v)
 for off,v in((0,bits(-9500.)),(4,bits(26214.40039)),(8,bits(.231))):put(m,COEF+off,v)
 return m
def fraction(c):return bits((c.seed%257)/256.)
def draw(c,n):return u32(0x93ac4d71+c.seed*0x12345+n*0xabcdef01)
def point(c,n,i):return bits((c.seed-128)*(i-1)*.125+(n+1)*.375)
class Service:
 def __init__(self,m,c):self.m=m;self.c=c;self.calls=[];self.query=None;self.draws=0
 def invoke(self,t,args):
  m,c=self.m,self.c;n=len(self.calls);a=list(args);observed=b''
  if t==QUERY:
   self.query=args[0];assert args[3]==OWNER+0x34;a[0]='query';a[3]='ground';observed=data(m,args[0],12)
  elif t==CREATE:
   a[0]='descriptor';assert args[3]==OWNER+0x38;a[3]='ground-tail';observed=masked(m,args[0],28,DHOLES)
  elif t==COPY:
   assert args[0]==OUTPUT+0xb0 and args[2]==32;a[:2]=['payload-destination','payload-source'];observed=masked(m,args[1],32,PHOLES)
  self.calls.append((t,tuple(a),observed))
  if t==QUERY:put(m,OWNER+0x34,bits((c.seed-128)*.5))
  if c.mutation&1 and self.query is not None:
   for i in range(3):put(m,self.query+4*i,point(c,n,i))
  if c.mutation&2 and t in(SELECT,FLOAT):put(m,OWNER+0x34,bits((n+1)*(c.seed-100)*.25))
  if c.mutation&4 and t==FLOAT:
   put(m,COEF+4,bits((c.seed-120)*127.5));put(m,COEF+8,bits((c.seed+1)/512.))
   for i in range(768):m[TABLE+i]=(c.seed+i*17+n)&255
  if c.mutation&8 and t==INT:
   put(m,COEF+4,bits(1.25));put(m,COEF+8,bits(.5));put(m,OWNER+0x70,0x88888888)
  if c.mutation&16 and t==CREATE:put(m,OWNER+0x70,0x77777777)
  put(m,MARK,u32(0x13579bdf+n*0x10203+t))
  if t==QUERY:return 0 if c.route==1 else 1
  if t==SELECT:return c.seed&255
  if t==FLOAT:return fraction(c)
  if t==INT:
   value=draw(c,self.draws);self.draws+=1;return value
  if t==CREATE:return OUTPUT if c.route==3 else 0
  if t==COPY:
   b=data(m,args[1],args[2])
   for i,v in enumerate(b):m[args[0]+i]=v
   return args[0]
  raise AssertionError(t)
def reference(initial,c):
 m=dict(initial);s=Service(m,c);home=STACK+c.phase;q=home-24;packet=home-96;desc=home-64
 if read(m,OWNER+0x70):m[read(m,OWNER+0x70)+0xb4]=1;return m,s.calls
 actor=read(m,OWNER+0x18);h=read(m,actor+0x118)
 upper=fp(h,bits(100.),'add','left')if floating(read(m,COEF))<floating(h)else fp(read(m,actor+0x18),bits(150.),'add','left')
 for off,v in((0,read(m,actor+0x14)),(4,upper),(8,read(m,actor+0x1c))):put(m,q+off,v)
 lower=fp(upper,bits(300.),'sub','left')
 if not s.invoke(QUERY,(q,0,lower,OWNER+0x34)):return m,s.calls
 selector=s.invoke(SELECT,());put(m,q+4,read(m,OWNER+0x34));f=s.invoke(FLOAT,())
 scale=fp(fp(f,bits(30.),'mul','left'),bits(50.),'add','left');base=read(m,COEF+4);rate=read(m,COEF+8)
 put(m,packet,OWNER);m[packet+4]=1
 for off,v in((8,base),(12,bits(32768.)),(16,0),(28,rate)):put(m,packet+off,v)
 for off,v in((20,0),(22,10),(24,10)):put(m,packet+off,v,2)
 angle=fp(fp(bits(32768.),bits(.5),'mul','left'),base,'add','left')
 put(m,desc,0x60300);put(m,desc+4,300,2);m[desc+6]=0x38;put(m,desc+8,0);put(m,desc+12,int(floating(angle)))
 for off,v in((16,150),(17,255),(18,m[TABLE+selector*3]),(19,m[TABLE+selector*3+1]),(20,m[TABLE+selector*3+2]),(21,255),(22,0),(23,6)):m[desc+off]=v
 put(m,desc+24,0x440001)
 first=s.invoke(INT,());second=s.invoke(INT,());third=s.invoke(INT,())
 args=(desc,7,1,OWNER+0x38,read(m,q),read(m,q+4),read(m,q+8),scale,scale,first&255,((third&1)<<1)+(second&1),32,255,1)
 result=s.invoke(CREATE,args);put(m,OWNER+0x70,result)
 if result:s.invoke(COPY,(result+0xb0,packet,32))
 return m,s.calls
class Oracle(FactoryOracle):
 def __init__(self,words,initial,c):
  super().__init__(words,initial,c,entry=ENTRY,s={},arguments=(OWNER,));self.service=Service(self.memory,c);self.saved=tuple(self.r[16:24]);self.saved_fp=tuple(self.f[20:])
 def execute(self,w):
  if w>>26==17 and w>>21&31==16 and w&63 in(0,1,2,3):self.f[w>>6&31]=fp(self.f[w>>11&31],self.f[w>>16&31],('add','sub','mul','div')[w&63],'left');return
  return super().execute(w)
 def record_call(self,t):assert t in COUNTS,hex(t);self.pending=t,tuple(self.arguments(COUNTS[t]))
 def hook(self,t):
  target,args=self.pending;assert target==t;answer=self.service.invoke(t,args)
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi=self.lo=0xdeadbeef
  if t==FLOAT:self.f[0]=answer
  else:self.r[2]=answer
def public(m):
 holes={OUTPUT+0xb0+i for i in PHOLES}
 return{p:v for p,v in m.items()if not STACK-4096<=p<STACK+1024 and p not in holes}
def verify(words,c):
 initial=fixture(c);expected,calls=reference(initial,c);m=Oracle(words,initial,c).run()
 assert public(m.memory)==public(expected),('public',asdict(c),next(((hex(p),v,expected.get(p))for p,v in public(m.memory).items()if v!=public(expected).get(p)),None))
 assert m.service.calls==calls,('calls',asdict(c),next(((i,a,b)for i,(a,b)in enumerate(zip(m.service.calls,calls))if a!=b),None))
 assert tuple(m.r[16:24])==m.saved and tuple(m.f[20:])==m.saved_fp
 return m
def programs():
 result={'retail':list(struct.unpack('>166I',(P/'retail.bin').read_bytes()))}
 for label,file in(('raw','v42.o'),('strict','ground-link-padded-strict.o'),('layout','ground-link-padded-layout.o')):
  b,r=payload(P/file,'func_151AADF8');result[label]=bound_blob(b,r,SYMS)
 return result
def main():
 code=programs();seen={k:set()for k in code};n=0
 for c in cases():
  for label,words in code.items():seen[label].update(verify(words,c).visits)
  n+=1
 controls=[];words=code['raw'];c=Case(2,3,31,8)
 for label,old,new in(('raise-offset',0x3c0142c8,0x3c0142ca),('notification-byte',0xa04f0004,0xa04f0005),('descriptor-flags',0x35290300,0x35290301),('factory-kind',0x24050007,0x24050008)):
  bad=words[:];assert bad.count(old)==1,(label,hex(old));bad[bad.index(old)]=new
  try:verify(bad,c if label!='notification-byte'else Case(6,0,0,8))
  except(AssertionError,ValueError,KeyError):controls.append(label)
  else:raise AssertionError(('ineffective control',label))
 report=dict(cases_per_stream=n,streams=list(code),words_visited={k:len(v)for k,v in seen.items()},payload_defined_bytes=27,payload_holes_uncredited=list(PHOLES),descriptor_defined_bytes=27,descriptor_holes_uncredited=list(DHOLES),effective_controls=controls,helpers_executed=False,whole_private_state_proof=False,source_installed=source.installed(),c_match_credit=0)
 (P/'guest-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
