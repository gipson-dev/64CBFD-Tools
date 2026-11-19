"""Independent attached-emitter reference with retained mutable provider buffers."""
from dataclasses import dataclass,replace
import itertools,json,struct
from tools.experiments import game_attached_accumulator_150ba55c_recovery as s
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.game_quaternion_matrix_1504a140_oracle import fp
from tools.tests.test_game_point_transform_match import put,read
RNG,REAL,TRANSFORM,DIRECTION,SUBMIT=0x150ADA20,0x150ADA68,0x1515c244,0x15143794,0x1518a3c0
COUNTS={RNG:0,REAL:0,TRANSFORM:4,DIRECTION:4,SUBMIT:13}
RECORD,ACTOR,OTHER,MARK=0x30000,0x60000,0x80000,0x70000
DT=0x800be9a4;CONSTANTS=tuple(range(0x8009fe30,0x8009fe5c,4))
ENTRY=s.ENTRY
u32=lambda n:n&0xffffffff
data=lambda m,p,n:bytes(m[p+i]for i in range(n))
public=lambda m:{p:v for p,v in m.items()if not STACK-2048<=p<STACK+2048}
def add(a,b):return fp(a,b,'add','left')
def sub(a,b):return fp(a,b,'sub','left')
def mul(a,b):return fp(a,b,'mul','left')
def short(n):return u32(((n&65535)^32768)-32768)
@dataclass(frozen=True)
class Case:
 seed:int=0;route:int=3;mutation:int=0;phase:int=0;time:int=0
TIMES=(0.,1.,1.0000001192092896,2.,3.5,-1.,float('nan'),float('inf'),float('-inf'),16777216.)
def cases():
 for seed,route in itertools.product(range(256),range(4)):yield Case(seed,route,seed%32,(seed&1)*8,seed%6)
 for seed,mutation,phase,time in itertools.product((0,1,127,255),(0,1,2,4,8,16,31),(0,8),range(10)):yield Case(seed,3,mutation,phase,time)
def layout(home,kind):
 shift=4 if kind=='raw'else 0
 return{n:home+off+shift for n,off in dict(origin=-24,radius=-28,height=-32,acceleration=-44,position=-60,rotation=-72,velocity=-84).items()}
def fixture(c):
 m={STACK+i:(i*17+c.seed*13+165)&255 for i in range(-2048,2048)}
 for base,n in((RECORD,128),(ACTOR,512),(OTHER,512),(MARK,4),(DT,4),(CONSTANTS[0],44)):
  m.update({base+i:(i*29+c.seed*11+90)&255 for i in range(n)})
 put(m,RECORD+40,ACTOR);m[RECORD+44]=c.seed;put(m,RECORD+48,bits(TIMES[c.time]));put(m,RECORD+14,15,2)
 for actor in(ACTOR,OTHER):
  put(m,actor,0 if c.route==0 else 1);m[actor+59]=(c.seed+int(c.route==1))&255;put(m,actor+468,0 if c.route==2 else 1)
  put(m,actor+0xf0,bits((-.5,0.,.75,1.25)[c.seed%4]));put(m,actor+0x14c,bits(3.25));put(m,actor+0x150,bits(4.75));put(m,actor+0x76,c.seed*257,2)
 for at,v in zip(CONSTANTS,(.25,.5,-.5,1.,2.,.125,3.,.75,4.,-2.,.875)):put(m,at,bits(v))
 put(m,DT,bits(.5));return m
class PrefixEnd(Exception):pass
class Service:
 def __init__(self,m,c):self.m=m;self.c=c;self.calls=[];self.random=0;self.reals=0;self.emissions=0;self.roles={}
 def norm(self,p):
  if p==ACTOR:return'actor'
  return next((n for n,a in self.roles.items()if p==a),p)
 def invoke(self,t,args):
  m,c=self.m,self.c;n=len(self.calls);a=list(args);observed=()
  if t==TRANSFORM:
   assert args[0]==ACTOR;self.roles.update(origin=args[1],radius=args[2],height=args[3]);a=[self.norm(p)for p in args]
  elif t==DIRECTION:self.roles['position']=args[3];a[3]='position'
  elif t==SUBMIT:
   if self.emissions==4:raise PrefixEnd()
   self.roles.update(position=args[0],rotation=args[1],velocity=args[3],acceleration=args[4]);a=[self.norm(p)if i in(0,1,3,4)else p for i,p in enumerate(args)]
   observed=tuple((name,data(m,self.roles[name],12))for name in('position','rotation','velocity','acceleration'));self.emissions+=1
  self.calls.append((t,tuple(a),observed))
  if c.mutation&1:
   put(m,RECORD+40,OTHER);m[RECORD+12]=(c.seed+n*7)&255;m[RECORD+1]=(c.seed+n*13)&255
   for at,v in((0xf0,.5+n*.125),(0x14c,40.+n),(0x150,60.+n)):put(m,ACTOR+at,bits(v))
   put(m,ACTOR+0x76,n*313,2)
  if c.mutation&2:
   for i,at in enumerate(CONSTANTS):put(m,at,bits((i+1)*.125+n*.015625))
   put(m,DT,bits(.25))
  if c.mutation&4:
   for name in('origin','radius','height'):
    if name in self.roles:
     for i in range(3 if name=='origin'else 1):put(m,self.roles[name]+4*i,bits((c.seed-100)*.125+n*.25+i))
  if c.mutation&8:
   for name in('position','rotation','velocity','acceleration'):
    if name in self.roles:
     for i in range(3):
      if name=='acceleration'and i==1 and t!=SUBMIT:continue
      put(m,self.roles[name]+4*i,bits((c.seed-80)*.25+n+i))
  if c.mutation&16 and t==SUBMIT:put(m,RECORD+48,bits(2.25 if self.emissions==1 else .25))
  put(m,MARK,u32(0x13579bdf+n*0x10203+t))
  if t==RNG:
   v=u32((0,0xffffffff,0x80000000,0x7fffffff,126,127,30,31)[(c.seed+self.random)%8]+self.random*0x1020304);self.random+=1;return v
  if t==REAL:
   v=bits(((c.seed+self.reals*37)%257)/256.);self.reals+=1;return v
  if t==TRANSFORM:
   for i in range(3):put(m,args[1]+4*i,bits((c.seed-128)*(i+1)*.125))
   put(m,args[2],bits(2.5));put(m,args[3],bits(3.75))
  if t==DIRECTION:
   for i in range(3):put(m,args[3]+4*i,bits((c.seed%17-8)*.25+i+.5))
  return 0x12345678
def reference(initial,c,kind='retail',home=None):
 m=dict(initial);v=layout(STACK+c.phase if home is None else home,kind);service=Service(m,c);actor=read(m,RECORD+40)
 def load(name,i=0):return read(m,v[name]+4*i)
 def store(name,i,value):put(m,v[name]+4*i,value)
 if not read(m,actor)or m[RECORD+44]!=m[actor+59]:put(m,RECORD+14,65535,2);return m,service,False
 if not read(m,actor+468):return m,service,False
 sample=service.invoke(REAL,());put(m,RECORD+48,add(read(m,RECORD+48),mul(add(read(m,CONSTANTS[0]),mul(sample,read(m,CONSTANTS[1]))),read(m,DT))))
 if not 1.<floating(read(m,RECORD+48)):return m,service,False
 size=mul(add(read(m,actor+0x14c),read(m,actor+0x150)),bits(.5));heading=(read(m,actor+0x76,2)>>8)-64
 service.invoke(TRANSFORM,(actor,v['origin'],v['radius'],v['height']))
 base,scale=(read(m,at)for at in CONSTANTS[2:4]);store('acceleration',1,0)
 try:
  while True:
   first=service.invoke(RNG,());second=service.invoke(RNG,());service.invoke(DIRECTION,(short(first%127+heading-63),short(second%31-50),load('radius'),v['position']))
   store('position',1,mul(load('position',1),read(m,actor+0xf0)))
   for i in range(3):store('position',i,add(load('position',i),load('origin',i)))
   for i in range(3):store('rotation',i,mul(service.invoke(REAL,()),bits(360.)))
   sample=service.invoke(REAL,());spread=add(mul(sample,read(m,CONSTANTS[4])),read(m,CONSTANTS[5]))
   for i in range(3):store('velocity',i,mul(sub(load('position',i),load('origin',i)),spread))
   for i in(0,2):store('acceleration',i,add(mul(service.invoke(REAL,()),scale),base))
   size_sample=service.invoke(REAL,());speed_sample=service.invoke(REAL,());duration=service.invoke(RNG,())
   service.invoke(SUBMIT,(v['position'],v['rotation'],mul(add(mul(size_sample,read(m,CONSTANTS[6])),read(m,CONSTANTS[7])),size),v['velocity'],v['acceleration'],add(mul(speed_sample,read(m,CONSTANTS[8])),read(m,CONSTANTS[9])),read(m,CONSTANTS[10]),7,duration%41+60,0,0,m[RECORD+12],m[RECORD+1]))
   put(m,RECORD+48,sub(read(m,RECORD+48),bits(1.)))
   if not 1.<floating(read(m,RECORD+48)):return m,service,False
 except PrefixEnd:return m,service,True
class Oracle(FactoryOracle):
 def __init__(self,words,initial,c):
  super().__init__(words,initial,c,entry=s.ENTRY,s={},arguments=(RECORD,));self.service=Service(self.memory,c);self.saved={i:self.r[i]for i in(*range(16,24),28,29,30)};self.saved_fp=tuple(self.f[20:])
 def execute(self,w):
  if w>>26==17 and w>>21&31==16 and w&63 in(0,1,2,3):self.f[w>>6&31]=fp(self.f[w>>11&31],self.f[w>>16&31],('add','sub','mul','div')[w&63],'left');return
  return super().execute(w)
 def record_call(self,t):assert t in COUNTS,hex(t);self.pending=t,tuple(self.arguments(COUNTS[t]))
 def hook(self,t):
  target,args=self.pending;assert target==t;answer=self.service.invoke(t,args)
  for i in range(max(4,COUNTS[t])):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi=self.lo=0xdeadbeef
  if t==REAL:self.f[0]=answer
  else:self.r[2]=answer
def verify(words,c,kind):
 initial=fixture(c);expected,service,prefix=reference(initial,c,kind);machine=Oracle(words,initial,c);stopped=False
 try:machine.run()
 except PrefixEnd:stopped=True
 assert prefix==stopped,('prefix',c)
 assert public(machine.memory)==public(expected),('public',c,next(((hex(p),a,expected.get(p))for p,a in public(machine.memory).items()if a!=expected.get(p)),None))
 assert machine.service.calls==service.calls,('calls',c,next(((i,a,b)for i,(a,b)in enumerate(zip(machine.service.calls,service.calls))if a!=b),None),len(machine.service.calls),len(service.calls))
 if not prefix:assert all(machine.r[i]==v for i,v in machine.saved.items())and tuple(machine.f[20:])==machine.saved_fp
 return machine,prefix
def run(state):
 seen={label:set()for label in('raw','retail')};n=prefixes=0
 for c in cases():
  for label in seen:
   machine,prefix=verify(state[label+'_words'],c,label);seen[label]|=machine.visits;prefixes+=int(prefix)
  n+=1
 report=dict(passes=True,cases_per_stream=n,streams=list(seen),words_visited={k:len(v)for k,v in seen.items()},bounded_nontermination_prefixes_per_stream=prefixes//2,termination_claim=False,retained_buffers_mutable=True,source_installed=False,c_match_credit=0)
 (s.OUT/'guest-report.json').write_text(json.dumps(report,indent=2)+'\n');return report
