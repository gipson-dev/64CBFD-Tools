"""Instruction-derived strip-update model; disjoint bounded caller objects."""
from pathlib import Path
from dataclasses import dataclass,asdict,replace
import hashlib,itertools,json,math,struct,sys
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.game_quaternion_matrix_1504a140_oracle import fp,is_nan
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments import game_strip_update_151ad174_private_recovery as source
P,R,ENTRY=source.OUT,source.ROOT,source.ENTRY
SYMS={row[1]:row[2][1]for row in symbol_rows((source.FROZEN/'conker/build/conker.us.elf').read_bytes())}
RECORD,POINTS,OTHER_POINTS,OWNER,OTHER_OWNER,EFFECT,OTHER_EFFECT,MARK=0x30000,0x50000,0x51000,0x60000,0x61000,0x70000,0x71000,0x72000
SIN,COS,QUERY,RNG,EMIT=[SYMS[n]for n in('func_150489B0','func_15048A40','func_1000F3D0','func_150ADA20','func_10010E78')]
TICKS,CATEGORY=SYMS['D_800BE9E4'],SYMS['D_800BE9F0'];COUNTS={SIN:1,COS:1,QUERY:1,RNG:0,EMIT:11}
CONSTANTS=source.PIN['constants']
u32=lambda n:n&0xffffffff
signed=lambda n:((n&0xffffffff)^0x80000000)-0x80000000
half=lambda n:((n&65535)^32768)-32768
dbits=lambda x:struct.unpack('>Q',struct.pack('>d',x))[0]
double=lambda n:struct.unpack('>d',struct.pack('>Q',n))[0]
add=lambda a,b:fp(a,b,'add');sub=lambda a,b:fp(a,b,'sub');mul=lambda a,b:fp(a,b,'mul');div=lambda a,b:fp(a,b,'div')
def square_root(n):
 if is_nan(n):return n|0x400000
 x=floating(n);return bits(math.sqrt(x))if x>=0 else 0x7fc00000
def narrow(n):
 x=floating(n)
 return u32(int(x))if math.isfinite(x)and -2147483648<=x<2147483648 else 0x80000000
def smooth(v,s,coefficient):return bits(floating(v)+floating(s)*coefficient)

@dataclass(frozen=True)
class Case:
 seed:int=0;count:int=20;owner:int=0;impulse:int=0;category:int=0;phase:int=0
 status:int=0;ticks:int=1;pattern:int=0;handle:int=0;query:int=0;random:int=0;mutation:int=0;remaining:int=2;z_velocity:int=0x41600000

REGIONS=((RECORD,128),(POINTS,480),(OTHER_POINTS,480),(OWNER,0x340),(OTHER_OWNER,0x340),(EFFECT,0xC0),(OTHER_EFFECT,0xC0),(MARK,4))
def fixture(c):
 m={STACK+i:(i*17+c.seed*13+0xa5)&255 for i in range(-4096,512)}
 for at,n in REGIONS:m.update({at+i:(i*29+c.seed*11+0x5a)&255 for i in range(n)})
 for base in(POINTS,OTHER_POINTS):
  for i in range(20):
   patterns=((i*.25,200.-i*19.,-i*.5,.125,0.,-.25),(1200.+i,20.-i*9.,3.*i,1000.,-2000.,500.),(0.,0.,0.,0.,0.,0.),(-20.+i*3.,i*11.,5.-i,-400.,20.,700.),(float(i%3),float(i%2),float(i%5),1e-12,-1e-12,1e-12))
   values=(0.,200.-i*19.,0.,0.,0.,floating(c.z_velocity))if c.pattern==5 else patterns[c.pattern%5]
   for j,v in enumerate(values):put(m,base+24*i+4*j,bits(v+(2.5 if base==OTHER_POINTS and c.pattern!=2 else 0.)))
 put(m,RECORD+0x38,POINTS);put(m,RECORD+0x3C,bits(19.));m[RECORD+0x42]=c.count
 put(m,RECORD+0x44,OWNER if c.owner else 0);put(m,RECORD+0x4C,bits(50. if c.impulse else 0.));m[RECORD+0x50]=(c.seed*53)&255;m[RECORD+0x51]=c.seed%20
 put(m,RECORD+0x52,c.status,2);put(m,RECORD+0x54,c.handle,2)
 for base,child in((OWNER,EFFECT),(OTHER_OWNER,OTHER_EFFECT)):
  put(m,base+0x31C,child);put(m,base+0x76,((c.seed*17+63)&255)<<8,2);put(m,base+0x3C,bits(1.25 if base==OWNER else -.75))
  put(m,child+0xA8,bits(2.5));m[child+0xAC]=(c.seed*29)&255;m[child+0xAD]=c.remaining;m[child+0xAE]=c.seed%20
 put(m,TICKS,c.ticks);put(m,CATEGORY,c.category)
 for n,item in CONSTANTS.items():
  raw=bytes.fromhex(item['bytes']);m.update({item['address']+i:v for i,v in enumerate(raw)})
 return m

class Service:
 def __init__(self,m,c):self.m=m;self.c=c;self.calls=[]
 def invoke(self,t,a):
  m,c=self.m,self.c;n=len(self.calls);self.calls.append((t,tuple(a)));put(m,MARK,u32(0x13579bdf+n*0x10203+t))
  if t in(SIN,COS):
   # A declared numeric-provider contract; original table functions are a separate connected gate.
   angle=a[0]&255;value=bits(math.sin((angle-(64 if t==COS else 0))*math.tau/256))
   if c.mutation&1 and n==0:
    put(m,RECORD+0x38,OTHER_POINTS);m[EFFECT+0xAE]=(c.seed+3)%20;put(m,OWNER+0x3C,bits(-2.));put(m,OWNER+0x76,0xA500,2)
    m[RECORD+0x42]=2;put(m,RECORD+0x4C,bits(-25.));m[RECORD+0x50]=91;m[RECORD+0x51]=(c.seed+1)%20
   if c.mutation&2 and n==1:put(m,RECORD+0x44,OTHER_OWNER);put(m,RECORD+0x38,POINTS)
   return value
  if t==QUERY:
   if c.mutation&4:put(m,RECORD+0x54,0x4321,2);put(m,RECORD+0x38,OTHER_POINTS)
   return c.query
  if t==RNG:
   if c.mutation&8:put(m,RECORD+0x38,OTHER_POINTS);put(m,CATEGORY,57);m[RECORD+0x50]=13
   return c.random
  assert t==EMIT
  return (c.seed*257+0xBEEF)&65535

def reference(initial,c):
 m=dict(initial);s=Service(m,c);getf=lambda p:read(m,p);putf=lambda p,v:put(m,p,v)
 status=half(read(m,RECORD+0x52,2))
 if status:
  status=half(status-read(m,TICKS));put(m,RECORD+0x52,max(status,0),2)
 last=m[RECORD+0x42]-1;owner=read(m,RECORD+0x44)
 def vp(i,j):return read(m,RECORD+0x38)+i*24+12+j*4
 def pp(i,j):return read(m,RECORD+0x38)+i*24+j*4
 if owner:
  effect=read(m,owner+0x31C);selected=m[effect+0xAE];angle=(m[effect+0xAC]+(read(m,owner+0x76,2)>>8))&255
  amplitude=mul(read(m,effect+0xA8),read(m,SYMS['D_800A9278']))
  value=s.invoke(SIN,(angle,));at=vp(selected,0);put(m,at,add(read(m,at),mul(amplitude,value)))
  value=s.invoke(COS,(angle,));at=vp(selected,2);put(m,at,sub(read(m,at),mul(amplitude,value)))
  owner=read(m,RECORD+0x44);angle=(read(m,owner+0x76,2)>>8)&255;amplitude=mul(read(m,owner+0x3C),bits(19.))
  value=s.invoke(SIN,(angle,));at=vp(selected,0);put(m,at,add(read(m,at),mul(amplitude,value)))
  value=s.invoke(COS,(angle,));at=vp(selected,2);put(m,at,sub(read(m,at),mul(amplitude,value)))
  at=vp(selected,1);put(m,at,sub(read(m,at),bits(1000.)))
  effect=read(m,read(m,RECORD+0x44)+0x31C);remaining=m[effect+0xAD]-1
  if remaining<=0:put(m,effect+0xA8,0);remaining=0;effect=read(m,read(m,RECORD+0x44)+0x31C)
  m[effect+0xAD]=remaining
 if floating(read(m,RECORD+0x4C))!=0.:
  value=s.invoke(SIN,(m[RECORD+0x50],));at=vp(m[RECORD+0x51],0);put(m,at,sub(read(m,at),mul(read(m,RECORD+0x4C),value)))
  value=s.invoke(COS,(m[RECORD+0x50],));at=vp(m[RECORD+0x51],2);put(m,at,add(read(m,at),mul(read(m,RECORD+0x4C),value)))
  put(m,RECORD+0x4C,mul(read(m,RECORD+0x4C),read(m,SYMS['D_800A927C'])))
 snapshot=[[read(m,pp(i,j))for j in range(3)]for i in range(last+1)]
 movement=0;damping=read(m,SYMS['D_800A9280']);ceiling=read(m,SYMS['D_800A9284']);coefficient=double(read(m,SYMS['D_800A9288'],8))
 for i in reversed(range(last)):
  position=list(snapshot[i]);velocity=[read(m,vp(i,j))for j in range(3)];d=[sub(position[j],snapshot[i+1][j])for j in range(3)]
  squares=[mul(x,x)for x in d];length=square_root(add(add(squares[0],squares[1]),squares[2]));horizontal=square_root(add(squares[0],squares[2]))
  if floating(length)==0.:length=bits(1.)
  lateral=mul(bits(9.),div(horizontal,length));square=mul(lateral,lateral);vertical=sub(bits(81.),square)
  vertical=square_root(vertical)if floating(square)<=81. else 0;ratio=div(vertical,length)
  force=[sub(0,mul(d[0],ratio)),sub(bits(-9.),mul(d[1],ratio)),sub(0,mul(d[2],ratio))]
  category=read(m,CATEGORY)
  for j in range(3):
   velocity[j]=mul(add(velocity[j],force[j]),damping)
   if i:
    smoothing=sub(mul(add(snapshot[i-1][j],snapshot[i+1][j]),bits(.5)),position[j]);velocity[j]=smooth(velocity[j],smoothing,coefficient)
   position[j]=add(position[j],velocity[j])
   if category==57 and floating(ceiling)<floating(position[0]):position[0]=ceiling
  d=[sub(position[j],read(m,pp(i+1,j)))for j in range(3)]
  movement=add(add(movement,velocity[0]&0x7fffffff),velocity[2]&0x7fffffff)
  length=square_root(add(mul(d[2],d[2]),add(mul(d[0],d[0]),mul(d[1],d[1]))))
  ratio=div(read(m,RECORD+0x3C),length)if floating(length)!=0. else bits(1.)
  for j in range(3):
   neighbor=read(m,pp(i+1,j));value=add(mul(sub(position[j],neighbor),ratio),neighbor);put(m,pp(i,j),value);put(m,vp(i,j),sub(value,snapshot[i][j]))
 if floating(movement)>250.:
  handle=read(m,RECORD+0x54,2)
  if not handle or not s.invoke(QUERY,(handle,)):
   random=s.invoke(RNG,());args=(0,random%9+0x507,30000,0,0,0,*map(narrow,position),250,u32(-0x7E0C));value=s.invoke(EMIT,args);put(m,RECORD+0x54,value,2)
 return m,s.calls

class Oracle(FactoryOracle):
 def __init__(self,words,initial,c):
  super().__init__(words,initial,c,entry=ENTRY,s={},arguments=(RECORD,));self.service=Service(self.memory,c)
  self.saved_g=tuple(self.r[16:24])+(self.r[28],self.r[29],self.r[30]);self.saved_fp=tuple(self.f[20:])
 def execute(self,w):
  op,fmt,ft,fs,fd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
  if op==17 and fmt==16:
   a,b=self.f[fs],self.f[ft]
   if fn in(0,1,2,3):self.f[fd]=fp(a,b,('add','sub','mul','div')[fn]);return
   if fn==4:self.f[fd]=square_root(a);return
   if fn in(5,7):self.f[fd]=a&0x7fffffff if fn==5 else a^0x80000000;return
   if fn==13:self.f[fd]=narrow(a);return
   if fn==33:
    n=dbits(floating(a));self.f[fd]=n&0xffffffff;self.f[fd+1]=n>>32;return
  if op==17 and fmt==17:
   a=double(self.f[fs+1]<<32|self.f[fs]);b=double(self.f[ft+1]<<32|self.f[ft])
   if fn in(0,2):
    n=dbits(a+b if fn==0 else a*b);self.f[fd]=n&0xffffffff;self.f[fd+1]=n>>32;return
   if fn==32:self.f[fd]=bits(a);return
  return super().execute(w)
 def record_call(self,t):assert t in COUNTS,hex(t);self.pending=t,tuple(self.arguments(COUNTS[t]))
 def hook(self,t):
  target,a=self.pending;assert t==target;result=self.service.invoke(t,a)
  for i in range(4):self.put(self.r[29]+i*4,0xb5000000+i,4)
  for i in(1,2,3,*range(4,16),24,25):self.r[i]=0xa5000000+i
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi=self.lo=0xdeadbeef
  if t in(SIN,COS):self.f[0]=result
  else:self.r[2]=result

def public(m):return {p:v for p,v in m.items()if not STACK-4096<=p<STACK+512}
def verify(words,c):
 initial=fixture(c);expected,calls=reference(initial,c);m=Oracle(words,initial,c).run()
 assert public(m.memory)==public(expected),('public',asdict(c),next(((hex(p),v,expected.get(p))for p,v in public(m.memory).items()if v!=expected.get(p)),None))
 assert m.service.calls==calls,('calls',asdict(c),m.service.calls,calls)
 assert tuple(m.r[16:24])+(m.r[28],m.r[29],m.r[30])==m.saved_g
 assert tuple(m.f[20:])==m.saved_fp
 return m

def cases():
 for seed in range(256):
  yield Case(seed,20,seed&1,(seed>>1)&1,(0,11,44,57)[seed%4],(seed&1)*8,(0,1,32767,32768,65535)[seed%5],(0,1,65535,0x7fffffff,0x80000000)[seed%5],seed%5,(0,1,65535)[seed%3],seed%3,(0,0x80000000,0xffffffff)[seed%3],seed%16,(0,1,2,255)[seed%4])
 for count,owner,impulse,pattern,category in itertools.product((0,1,2,3,19,20),(0,1),(0,1),range(5),(0,57)):
  yield Case(7,count,owner,impulse,category,8,65535,1,pattern,65535,0,0xffffffff,0,1)
 for count,z,handle,query in itertools.product((19,20),(13.,13.5,13.7,14.,15.,-14.),(0,65535),(0,1)):
  yield Case(count=count,pattern=5,handle=handle,query=query,z_velocity=bits(z))

def main():
 out=P;raw,refs=payload(out/'owner.o','func_151AD174');programs={'retail':list(struct.unpack('>494I',(out/'retail.bin').read_bytes())),'raw':bound_blob(raw,refs,SYMS)}
 seen={k:set()for k in programs};n=0;controls=[]
 for c in cases():
  for k,words in programs.items():seen[k].update(verify(words,c).visits)
  n+=1
  if n%128==0:print(json.dumps(dict(cases=n)),flush=True)
 report=dict(cases=n,streams=list(programs),words_visited={k:len(v)for k,v in seen.items()},unvisited={k:[hex(i*4)for i in range(len(w))if ENTRY+i*4 not in seen[k]]for k,w in programs.items()},public_bytes_and_calls_equal=True,full_preserved_registers=True,source_installed=False,c_match_credit=0,domain='Fresh disjoint objects, count 0..20, finite coordinate fixtures; opaque mutable numeric/audio providers. FP status and private stack equivalence not established.')
 (out/'guest-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
