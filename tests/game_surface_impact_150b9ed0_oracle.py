"""Independent finite surface-impact model and execution of both MIPS streams."""
from dataclasses import dataclass,replace
import itertools,json,math,struct
from tools.experiments import game_surface_impact_150b9ed0_screen as s
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests import test_game_point_interval_effect_match as fp
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary

STACK=fp.STACK;POINT=0x30000
GATE,QUERY,PREDICATE,RNG,REAL,FACTORY,SPRAY=0x150A3058,0x150AC9C0,0x15145C90,0x150ADA20,0x150ADA68,0x1513C650,0x151511FC
CODE,FLAG=0x151E7EF8,0x80084060
CONSTANTS=tuple(range(0x8009FE10,0x8009FE2C,4))
BURST_FIELDS=tuple(range(0x1C))+tuple(range(0x22,0x26))
SPRAY_FIELDS=tuple(i for i in range(116)if i not in(0x2e,0x2f,0x4a,0x4b,0x5e,0x5f))
assert len(BURST_FIELDS)==32 and len(SPRAY_FIELDS)==110
put,read=fp.put,fp.read;u32=fp.u32;bits,floating=fp.bits,fp.floating
COORDS=((0.,-0.,0.),(-0.,0.,-0.),(17.75,-91.5,255.25),(-17.75,91.5,-255.25),
        (32768.75,-32769.75,65535.5),(-65536.5,1000000.25,-1000000.25),
        (1.25,-2.5,3.75),(100.,200.,300.))

@dataclass(frozen=True)
class Case:
 path:int=5;corrupt:int=0;mutation:int=0;coords:int=0;mode:int=0xABCD00FF
 tag:int=0x87654321;seed:int=0;phase:int=0;flag:int=0x55

def layout(home,kind):
 offsets={'retail':dict(burst=-116,spray=-232,context=-72,position=-52,hit=-76),
          'raw':dict(burst=-88,spray=-204,context=-44,position=-24,hit=-48)}[kind]
 return {n:home+v for n,v in offsets.items()}

def args(c):return(0 if c.path==0 else POINT,bits(1.25),bits(-3.75),c.mode,c.tag)
def data(m,p,n):return bytes(m[p+i]for i in range(n))
def public(m):return{a:b for a,b in m.items()if not STACK-2048<=a<STACK+2048}
def add(a,b):return fp.single(floating(a)+floating(b))
def sub(a,b):return fp.single(floating(a)-floating(b))
def neg(a):return a^0x80000000
def signed16(a):return u32(((a&65535)^32768)-32768)
def randoms(c):return tuple(u32(v)for v in(0xffffffff^c.seed,c.seed*0x1020304,0x80000000+c.seed,0x7fffffff-c.seed,c.seed*0x1234567))
def reals(c):return(bits((.25,.5,.75,-.5)[c.seed%4]),bits((.75,.25,1.,0.)[c.seed%4]))

def fixture(c,kind='retail',home=None):
 home=STACK+c.phase if home is None else home;m={STACK+i:(i*17+c.seed*13+165)&255 for i in range(-2048,2048)}
 m.update({POINT+i:(i*13+c.seed*7+91)&255 for i in range(0x300)})
 for i,v in enumerate(COORDS[c.coords]):put(m,POINT+0x14+4*i,bits(v))
 for i,w in enumerate(s.checksum_words()):put(m,CODE+4*i,w^(1 if c.corrupt and i==7 else 0))
 m[FLAG]=c.flag
 for i,at in enumerate(CONSTANTS):put(m,at,bits((i+1)*.25))
 roles=layout(home,kind)
 for name,n in(('burst',40),('spray',116)):
  for i in range(n):m[roles[name]+i]=(i*29+c.seed*11+0x61)&255
 put(m,home+16,c.tag);return m

def point_effect(m,c,stage):
 if c.mutation&1:
  for i,v in enumerate((10.25+stage,-20.5-stage,30.75+stage)):put(m,POINT+0x14+4*i,bits(v))

def escaped_effect(m,c,roles,stage):
 if c.mutation&2:
  for i,v in enumerate((-7.25-stage,8.5+stage,-9.75-stage)):put(m,roles['position']+4*i,bits(v))
 if c.mutation&4:
  for i in range(18):m[roles['context']+i]=(i*37+c.seed+stage)&255
 if c.mutation&8:
  for i,at in enumerate(CONSTANTS):put(m,at,bits((i+1)*.5+stage))

def query_effect(m,c,roles):
 for i,v in enumerate((1.25,-2.5,3.75)):put(m,roles['position']+4*i,bits(v))
 for i in range(18):m[roles['context']+i]=(i*29+c.seed+0x31)&255
 put(m,roles['hit'],0x87654321);point_effect(m,c,3)

def reference(initial,c,kind='retail',home=None):
 home=STACK+c.phase if home is None else home;m=dict(initial);roles=layout(home,kind);calls=[];observations=[]
 def call(t,a=()):
  a=tuple(map(u32,a));calls.append((t,a))
  if t in(FACTORY,SPRAY):observations.append((t,data(m,a[0],40 if t==FACTORY else 116)))
 def field(name,off,v,n=4):put(m,roles[name]+off,v,n)
 if c.path==0:return public(m),calls,observations
 checksum=sum((~read(m,CODE+4*i))&0xffffffff for i in range(26))&0xffffffff
 if checksum!=0x3843095e:m[FLAG]=255
 for subtype in(2,1):
  coords=tuple(signed16(math.trunc(floating(read(m,POINT+0x14+4*i))))for i in range(3))
  call(GATE,(subtype,*coords));point_effect(m,c,3-subtype)
  if c.path==(1 if subtype==2 else 2):return public(m),calls,observations
 dx=neg(sub(read(m,POINT+0x14),bits(1.25)));dz=neg(sub(read(m,POINT+0x1c),bits(-3.75)))
 call(QUERY,(read(m,POINT+0x14),add(read(m,POINT+0x18),bits(80.)),read(m,POINT+0x1c),dx,0,dz,0,roles['context'],roles['position'],roles['position']+4,roles['position']+8,0,roles['hit'],0,0))
 query_effect(m,c,roles)
 if c.path==3:return public(m),calls,observations
 call(PREDICATE,(read(m,roles['hit']),));escaped_effect(m,c,roles,4)
 if c.path==5:
  field('burst',6,6,1);field('burst',7,0,1);field('burst',0,0x9f01)
  call(RNG);escaped_effect(m,c,roles,5);field('burst',4,randoms(c)[0]%51+100,2)
  field('burst',8,0);field('burst',12,0)
  call(RNG);escaped_effect(m,c,roles,6);field('burst',0x10,randoms(c)[1]%101+155,1)
  for i in range(0x11,0x16):field('burst',i,255,1)
  field('burst',0x18,0x3b0002);field('burst',0x16,0,1);field('burst',0x17,7,1)
  field('burst',0x22,25,2);field('burst',0x24,10,2)
  call(REAL);escaped_effect(m,c,roles,7);call(REAL);escaped_effect(m,c,roles,8)
  for i in range(3):call(RNG);escaped_effect(m,c,roles,9+i)
  scale=tuple(add(fp.product(v,bits(20.)),bits(40.))for v in reals(c))
  r0,r1,r2=randoms(c)[2:]
  call(FACTORY,(roles['burst'],0,0,roles['context'],*(read(m,roles['position']+4*i)for i in range(3)),*scale,r0&255,(r2&1)+((r1&1)<<1),3,255,0,c.mode&255,c.tag))
  escaped_effect(m,c,roles,12)
 field('spray',0,15,2);field('spray',2,10,2)
 for i in range(12):m[roles['spray']+4+i]=m[roles['position']+i]
 field('spray',0x10,neg(dx));field('spray',0x14,0x80000000);field('spray',0x18,neg(dz))
 for i in range(18):m[roles['spray']+0x1c+i]=m[roles['context']+i]
 for off,v,n in((0x30,read(m,CONSTANTS[0]),4),(0x34,7,1),(0x35,0,1),(0x36,0x3b01,2),(0x38,26,2),(0x3a,20,2),(0x3c,bits(7.),4),(0x40,bits(10.),4),(0x44,0x5c0001,4),(0x48,100,1),(0x49,155,1),(0x5c,0,1),(0x5d,7,1),(0x60,3,4),(0x64,255,4),(0x68,10,2),(0x6a,25,2)):
  field('spray',off,v,n)
 for off,at in zip((0x4c,0x50,0x54,0x58,0x6c,0x70),CONSTANTS[1:]):field('spray',off,read(m,at))
 call(SPRAY,(roles['spray'],c.mode&255,c.tag));return public(m),calls,observations

class Oracle(FactoryOracle):
 def __init__(self,words,c,kind='retail',initial=None,home=None,entry=s.ENTRY,connected=None):
  self.cc=c;self.kind=kind;self.home=STACK+c.phase if home is None else home
  self.roles=layout(self.home,kind);self.ri=self.fi=self.gi=0;self.obs=[]
  super().__init__(words,fixture(c,kind,self.home)if initial is None else initial,c,entry=entry,arguments=args(c),connected=connected)
 def execute(self,w):
  op,rs,rt,rd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w&63
  if op==0 and fn==39:self.r[rd]=u32(~(self.r[rs]|self.r[rt]));self.r[0]=0
  elif op==17 and rs==16 and fn==7:self.f[w>>6&31]=neg(self.f[w>>11&31])
  elif op in(42,46):
   at=u32(self.r[rs]+((w&65535)^32768)-32768);v=self.r[rt];k=at&3
   if op==42:self.put(at,v>>(8*k),4-k)
   else:self.put(at&~3,v,k+1)
  else:super().execute(w)
 def record_call(self,t):
  n={s.ENTRY:5,GATE:4,QUERY:15,PREDICATE:1,RNG:0,REAL:0,FACTORY:16,SPRAY:3}[t]
  a=tuple(map(u32,self.arguments(n)))
  if t==QUERY:a=(self.f[12],self.f[14],*a[2:])
  self.calls.append((t,a))
  if t in(FACTORY,SPRAY):self.obs.append((t,data(self.memory,a[0],40 if t==FACTORY else 116)))
 def hook(self,t):
  c=self.cc;m=self.memory;value=0x87654321;fvalue=None
  if t==GATE:
   self.gi+=1;point_effect(m,c,self.gi);value=int(c.path==self.gi)
  elif t==QUERY:query_effect(m,c,self.roles);value=int(c.path!=3)
  elif t==PREDICATE:escaped_effect(m,c,self.roles,4);value=int(c.path==5)
  elif t==RNG:
   value=randoms(c)[self.ri];escaped_effect(m,c,self.roles,5+self.ri if self.ri<2 else 7+self.ri);self.ri+=1
  elif t==REAL:fvalue=reals(c)[self.fi];escaped_effect(m,c,self.roles,7+self.fi);self.fi+=1
  elif t==FACTORY:escaped_effect(m,c,self.roles,12)
  else:assert t==SPRAY
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.r[2]=u32(value)
  self.hi,self.lo=0xa5000010,0xa5000011
  if fvalue is not None:self.f[0]=fvalue

def cases():
 for i,(path,corrupt,mutation,coords,phase)in enumerate(itertools.product(range(6),range(2),(0,1,2,4,8,3,7,15),range(8),(0,8))):
  yield Case(path,corrupt,mutation,coords,u32(0xabcd0000|i&255),u32(0x87654321+i*0x1020304),i,phase,(0,0x55,0xff)[i%3])
 for i in range(256):yield Case(mode=0xabcd0000|i,seed=i,mutation=i%16,coords=i%8,corrupt=i%2)

def compare(words,c,kind):
 initial=fixture(c,kind);m=Oracle(words,c,kind,initial);gpr,fpr=m.r[:],m.f[:];m.run()
 assert(public(m.memory),m.calls,m.obs)==reference(initial,c,kind),(kind,c,m.calls,m.obs,reference(initial,c,kind)[1:])
 assert m.r[16:24]==gpr[16:24]and m.r[28:]==gpr[28:]and m.f[20:]==fpr[20:],(kind,c,'saved ABI')
 return m

def run(state):
 seen={k:set()for k in('retail','raw')};count=0
 for c in cases():
  for kind in seen:seen[kind].update(compare(state[kind+'_words'],c,kind).visits)
  count+=1
 assert all(len(v)==291 for v in seen.values()),{k:len(v)for k,v in seen.items()}
 report=dict(passes=True,cases_per_stream=count,words_visited={k:len(v)for k,v in seen.items()},descriptor_bytes=[40,116],unwritten_descriptor_bytes_preserved=[8,6],all_mode_bytes=True,finite_conversion_domain=True,provider_mutations=True,saved_ABI=True,raw_private_identity_claimed=False,source_installed=False,c_match_credit=0)
 (s.OUT/'guest-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report

def caller(state):
 start,end=0x15058bc0,0x15058c24;rom=(s.ROOT/'conker/conker.us.bin').read_bytes();body=list(struct.unpack_from('>25I',rom,0x86070));count=0
 for i,(kind,enabled,category,mutation,corrupt,coords)in enumerate(itertools.product(('retail','raw'),(0,1),(11,12,13),(0,1,2,4,8,15),(0,1),range(4))):
  c=Case(path=5,mutation=mutation,corrupt=corrupt,coords=coords,mode=255,tag=0,seed=i,phase=8*(i%2));h=STACK+c.phase;initial=fixture(c,kind)
  initial[POINT+4]=category;initial[POINT+0x24e]=enabled;put(initial,POINT+0x76,0x8765,2)
  code=dict(zip(range(s.ENTRY,s.ENTRY+1164,4),state[kind+'_words']));code[end]=0
  m=Oracle(body,c,kind,initial,entry=start,connected=code);m.r[16]=POINT;m.r[13]=0x12345678;m.f[0]=bits(1.25);m.f[2]=bits(-3.75)
  m.code=WindowCode(m.code,m);m.code.ends=(end,)
  try:m.run()
  except WindowBoundary:pass
  else:raise AssertionError('caller window did not reach its recorded boundary')
  called=enabled and category==12
  want,calls,obs=reference(initial,c,kind)if called else(public(initial),[],[])
  if called:calls=[(s.ENTRY,args(c))]+calls
  actual=public(m.memory);expected=dict(want);put(expected,POINT+0xf4,0x12355678)
  if enabled:
   expected[POINT+0x232]=enabled;expected[POINT+0x24e]=0;put(expected,POINT+0x218,0)
   put(expected,POINT+0x7a,0x8765,2);put(expected,POINT+0x78,0x8765,2)
  assert(actual,m.calls,m.obs)==(expected,calls,obs),(kind,c,category,enabled,m.calls,calls)
  assert m.r[29]==h and m.r[16]==POINT and m.f[0]==bits(1.25)and m.f[2]==bits(-3.75),(kind,c,'caller reloads and stack')
  count+=1
 report=dict(passes=True,cases=count,actual_caller_words=25,caller='func_15058898',mode_byte=255,tag_word=0,return_ignored=True,flag_reload_and_cleanup=True,full_caller_qualified=False,source_installed=False,c_match_credit=0)
 (s.OUT/'caller-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
