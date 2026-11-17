"""Independent actor-accumulator reference and mutable bounded provider contracts."""
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
from tools.experiments import game_actor_accumulator_151ab9c8_recovery as source
R,P,ENTRY=source.ROOT,source.OUT,source.ENTRY
RECORD,ACTOR,OTHER,MARK=0x30000,0x60000,0x80000,0x70000
DT,C0,C1=0x800BE9A4,0x800A9018,0x800A901C
RNG,REAL,ANGLE,HEIGHT,EMIT=0x150ADA20,0x150ADA68,0x151423D8,0x1504715C,0x151D9014
COUNTS={RNG:0,REAL:0,ANGLE:1,HEIGHT:2,EMIT:16}
SYMS={r[1]:r[2][1]for r in symbol_rows((R/'conker/build/conker.us.elf').read_bytes())}
u32=lambda n:n&0xffffffff
data=lambda m,p,n:bytes(m[p+i]for i in range(n))
class PrefixEnd(Exception):pass
@dataclass(frozen=True)
class Case:
 seed:int=0;route:int=3;mutation:int=0;phase:int=0;time:int=0
def cases():
 for seed,route in itertools.product(range(256),range(4)):yield Case(seed,route,seed%32,(seed&1)*8,0)
 for seed,mutation,phase,time in itertools.product((0,1,127,255),(0,1,2,4,8,16,31),(0,8),(1,2,3,4,5,6,7,8)):
  yield Case(seed,3,mutation,phase,time)
TIMES=(0x3f400000,0x3f800000,0x3f800001,0x40000000,0x40600000,0x7f800000,0x7fc00001,0xff800000,0x4b800000)
def fixture(c):
 assert all(not(STACK-4096<at+n and at<STACK+1024)for at,n in((RECORD,512),(ACTOR,512),(OTHER,512),(MARK,4)))
 m={STACK+i:(i*17+c.seed*13+0xa5)&255 for i in range(-4096,1024)}
 for at,n in((RECORD,512),(ACTOR,512),(OTHER,512),(MARK,4),(DT,4),(C0,8)):
  m.update({at+i:(i*29+c.seed*11+0x5a)&255 for i in range(n)})
 put(m,RECORD+0x28,ACTOR);m[RECORD+0x2c]=c.seed;put(m,RECORD+0x30,0x8000+c.seed)
 put(m,ACTOR,0 if c.route==0 else 1);m[ACTOR+0x3b]=(c.seed+int(c.route==1))&255;put(m,ACTOR+0x84,0x8000+c.seed+int(c.route==2),2)
 put(m,RECORD+0x34,TIMES[c.time]);put(m,RECORD+0x38,bits(0.0 if c.time else 1.25));put(m,RECORD+0x3c,bits(0.0 if c.time else .5));m[RECORD+0x40]=c.seed
 for a in(ACTOR,OTHER):
  for i in range(3):put(m,a+0x14+4*i,bits((c.seed-128)*(i+1)*.25))
 put(m,DT,bits(.5));put(m,C0,0x44324000);put(m,C1,0x3c23d70a)
 return m
class Service:
 def __init__(self,m,c):self.m=m;self.c=c;self.calls=[];self.random=0;self.reals=0;self.emissions=0;self.surface=None;self.position=None;self.velocity=None
 def invoke(self,t,args):
  m,c=self.m,self.c;n=len(self.calls);a=list(args);observed=b''
  if t==HEIGHT:
   self.surface=args[0];a[0]='surface'
   for i in range(36):m[self.surface+i]=(c.seed+i*7)&255
  elif t==EMIT:
   if self.emissions==4:raise PrefixEnd()
   self.position,self.velocity=args[:2];assert args[11]==self.surface
   a[0:2]=['position','velocity'];a[11]='surface'
   observed=data(m,args[0],12)+data(m,args[1],12)+data(m,self.surface,36);self.emissions+=1
  self.calls.append((t,tuple(a),observed))
  if c.mutation&1 and t in(REAL,RNG,ANGLE):
   actor=OTHER if n&1 else ACTOR;put(m,RECORD+0x28,actor)
   for i in range(3):put(m,actor+0x14+4*i,bits((c.seed-100)*(i+1)*.125+n*.5))
   m[RECORD+0x40]=(c.seed+n*13)&255;m[RECORD+0x0c]=(c.seed+n*7)&255;m[RECORD+1]=(c.seed+n*5)&255
  if c.mutation&2 and t==REAL:
   put(m,C0,bits(30.25+n));put(m,C1,bits(.125));put(m,DT,bits(.25))
   if n==0:
    put(m,RECORD+0x38,bits(.5));put(m,RECORD+0x3c,bits(.25));put(m,RECORD+0x34,bits(2.25))
  if c.mutation&4 and self.surface is not None:
   for i in range(36):m[self.surface+i]=(c.seed+n*11+i*3)&255
  if c.mutation&8 and self.position is not None:
   for at in(self.position,self.velocity):
    for i in range(3):put(m,at+4*i,bits(c.seed*.125+n+i))
  if c.mutation&16 and t==EMIT:put(m,RECORD+0x34,bits(.25 if self.emissions>=2 else 2.25))
  put(m,MARK,u32(0x13579bdf+n*0x10203+t))
  if t==RNG:
   value=u32((0,0xffffffff,0x80000000,0x7fffffff,25,26,100,101)[(c.seed+self.random)%8]+self.random*0x1020304);self.random+=1;return value
  if t==REAL:
   value=bits(((c.seed+self.reals*37)%257)/256.);self.reals+=1;return value
  if t==ANGLE:return bits(((args[0]*13+c.seed)%257-128)/128.)
  return 0x12345678
def reference(initial,c):
 m=dict(initial);s=Service(m,c);state=RECORD+40;home=STACK+c.phase;surface=home-44;position=home-56;velocity=home-68
 actor=read(m,state)
 if not read(m,actor)or m[state+4]!=m[actor+0x3b]or read(m,state+8)!=read(m,actor+0x84,2):put(m,RECORD+14,0xffff,2);return m,s.calls,False
 f=s.invoke(REAL,());time=fp(read(m,state+12),fp(fp(read(m,state+16),fp(f,read(m,state+20),'mul','left'),'add','left'),read(m,DT),'mul','left'),'add','left');put(m,state+12,time)
 if not floating(read(m,state+12))>1.:return m,s.calls,False
 s.invoke(HEIGHT,(surface,read(m,state)))
 try:
  while True:
   yaw=s.invoke(RNG,())&255;pitch=s.invoke(RNG,())%46-63
   p=s.invoke(ANGLE,(pitch&255,));pq=s.invoke(ANGLE,((pitch-64)&255,));y=s.invoke(ANGLE,(yaw,));yq=s.invoke(ANGLE,((yaw-64)&255,));sample=s.invoke(REAL,())
   radius=fp(bits(30.),p,'mul','left')
   put(m,position,fp(read(m,read(m,state)+0x14),fp(radius,yq,'mul','left'),'add','left'))
   put(m,position+4,fp(read(m,read(m,state)+0x18),fp(bits(75.),pq,'mul','left'),'sub','left'))
   put(m,position+8,fp(read(m,read(m,state)+0x1c),fp(radius,y,'mul','left'),'add','left'))
   speed=fp(fp(fp(sample,read(m,C0),'mul','left'),bits(500.),'add','left'),read(m,C1),'mul','left');radial=fp(speed,p,'mul','left')
   put(m,velocity,fp(radial,yq,'mul','left'));put(m,velocity+4,fp(speed^0x80000000,pq,'mul','left'));put(m,velocity+8,fp(radial,y,'mul','left'))
   bias=s.invoke(REAL,());lifetime=s.invoke(RNG,());opacity=s.invoke(RNG,());size=s.invoke(REAL,())
   s.invoke(EMIT,(position,velocity,m[state+24],fp(fp(bias,bits(.5),'mul','left'),bits(-1.),'add','left'),lifetime%26+32,opacity%101+100,fp(fp(size,bits(34.),'mul','left'),bits(52.),'add','left'),1,bits(1.),bits(1.),1,surface,1,0,m[RECORD+12],m[RECORD+1]))
   put(m,state+12,fp(read(m,state+12),bits(1.),'sub','left'))
   if not floating(read(m,state+12))>1.:return m,s.calls,False
 except PrefixEnd:return m,s.calls,True
class Oracle(FactoryOracle):
 def __init__(self,words,initial,c):
  super().__init__(words,initial,c,entry=ENTRY,s={},arguments=(RECORD,));self.service=Service(self.memory,c);self.saved=tuple(self.r[16:24]);self.saved_fp=tuple(self.f[20:]);self.saved_more=(self.r[28],self.r[30],self.r[29])
 def execute(self,w):
  if w>>26==17 and w>>21&31==16 and w&63 in(0,1,2,3):self.f[w>>6&31]=fp(self.f[w>>11&31],self.f[w>>16&31],('add','sub','mul','div')[w&63],'left');return
  if w>>26==17 and w>>21&31==16 and w&63==7:self.f[w>>6&31]=self.f[w>>11&31]^0x80000000;return
  return super().execute(w)
 def record_call(self,t):assert t in COUNTS,hex(t);self.pending=t,tuple(self.arguments(COUNTS[t]))
 def hook(self,t):
  target,args=self.pending;assert target==t;answer=self.service.invoke(t,args)
  for i in range(max(4,COUNTS[t])):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi=self.lo=0xdeadbeef
  if t in(REAL,ANGLE):self.f[0]=answer
  else:self.r[2]=answer
def public(m):return{p:v for p,v in m.items()if not STACK-4096<=p<STACK+1024}
def verify(words,c):
 initial=fixture(c);expected,calls,truncated=reference(initial,c);m=Oracle(words,initial,c);stopped=False
 try:m.run()
 except PrefixEnd:stopped=True
 assert stopped==truncated,('prefix',asdict(c))
 assert public(m.memory)==public(expected),('public',asdict(c),next(((hex(p),v,expected.get(p))for p,v in public(m.memory).items()if v!=expected.get(p)),None))
 assert m.service.calls==calls,('calls',asdict(c),len(m.service.calls),len(calls),next(((i,a,b)for i,(a,b)in enumerate(zip(m.service.calls,calls))if a!=b),None))
 if not stopped:assert tuple(m.r[16:24])==m.saved and tuple(m.f[20:])==m.saved_fp and(m.r[28],m.r[30],m.r[29])==m.saved_more
 return m,stopped
def programs():
 result={'retail':list(struct.unpack('>227I',(P/'retail.bin').read_bytes()))}
 for label,file in(('raw','v28.o'),('strict','actor-accumulator-padded-strict.o'),('layout','actor-accumulator-padded-layout.o')):
  b,r=payload(P/file,'func_151AB9C8');result[label]=bound_blob(b,r,SYMS)
 return result
def main():
 code=programs();seen={k:set()for k in code};n=prefixes=0
 for c in cases():
  for label,words in code.items():m,stopped=verify(words,c);seen[label].update(m.visits);prefixes+=int(stopped)
  n+=1
 report=dict(cases_per_stream=n,streams=list(code),words_visited={k:len(v)for k,v in seen.items()},bounded_nontermination_prefixes_per_stream=prefixes//len(code),public_actor_buffers_disjoint_from_private_stack=True,helpers_executed=False,source_installed=source.installed(),c_match_credit=0)
 (P/'guest-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
