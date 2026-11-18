"""Independent impact, descriptors, helper mutations and complete O32 execution."""
from dataclasses import dataclass
import itertools,json,math
from tools.experiments import game_impact_terminal_150b8f44_screen as s
from tools.tests import test_game_point_interval_effect_match as g
ENTRY=s.ENTRY;STACK=g.STACK;ACTOR,SURFACE,OUTPUT,SPRAY_OUTPUT=0x30000,0x70000,0x50000,0x60000
put,read=g.put,g.read;TILE,QUERY,CLASSIFY=0x150A3058,0x150AC9C0,0x15145C90
RNG,REAL,FACTORY,COPY,SPRAY,SOUND=0x150ADA20,0x150ADA68,0x1513D594,0x10022EC0,0x15151670,0x10010F88
sym=s.symbols();CONSTANTS=tuple(sym[n]for n in('D_8009FDBC','D_8009FDC0','D_8009FDC4','D_8009FDC8','D_8009FDCC','D_8009FDD0'));SOUNDS=sym['D_80088734'];ONE_SOUND=sym['D_8008873C'];ASSET=sym['D_800A4AA0']

@dataclass(frozen=True)
class Case:
 actor:int=ACTOR;mode:int=0;amount:int=0;phase:int=0;fcsr:int=0
 amplitude:int=0x42700000;vertical:int=0xC0000000
 tile:int=0;query:int=1;classify:int=1;success:int=1;mutation:int=0;flags:int=0;coordinate:int=0
 randoms:tuple=(0xffffffff,1,0,255,1);floats:tuple=(0x3f000000,0x3e800000)

def layout(h,kind):
 b=h-416;shift=4 if kind=='raw' else 0
 return {n:b+off+shift for n,off in(('burst',0x114),('extra',0x10c),('spray',0x68),('context',0x170),('position',0x184),('hit',0x16c))}

def fixture(c,kind='retail',home=None,surface=SURFACE):
 h=STACK+c.phase if home is None else home;m={STACK+i:(i*17+165)&255 for i in range(-2048,2048)}
 for base,n in((ACTOR,384),(SURFACE,64),(OUTPUT,512),(SPRAY_OUTPUT,164)):
  m.update({base+i:(i*13+91)&255 for i in range(n)})
 for name,n in(('burst',88),('extra',8),('spray',164),('context',18),('position',12),('hit',4)):
  at=layout(h,kind)[name]
  for i in range(n):m[at+i]=(i*29+0x61)&255
 for off,v in((8,g.bits(2.25)),(12,g.bits(6.25)),(16,g.bits(4.75))):put(m,h+off,v)
 for off,v in((0x14,.75),(0x38,9.5),(0x3c,10.25),(0x40,11.75),(0x44,1.25),(0x4c,3.75),(0x50,4.25),(0x54,5.5),(0x58,6.75)):put(m,ACTOR+off,g.bits(v))
 for off,v in((0x48,c.vertical),(0x140,c.amplitude),(0x128,0x12345678),(0x14c,0x23456789),(0x168,0x34567890)):put(m,ACTOR+off,v)
 m[ACTOR+1]=5;m[ACTOR+0xc]=255
 values=((12.75,-13.5,14.25),(32767.5,-32768.75,65535.),(-65535.,65534.,-.75))
 for i,v in enumerate(values[c.coordinate%3]):put(m,surface+0x14+4*i,g.bits(v))
 for a,v in zip(CONSTANTS,(.125,.25,.375,.5,.625,.75)):put(m,a,g.bits(v))
 put(m,SOUNDS,0x1234);put(m,SOUNDS+4,0x5678);put(m,ONE_SOUND,0x9abc);return m

def public(m):return{a:v for a,v in m.items()if not STACK-2048<=a<STACK+2048}
def add(a,b):return g.single(g.floating(a)+g.floating(b))
def subtract(a,b):return g.single(g.floating(a)-g.floating(b))
def trunc(a):return g.u32(math.trunc(g.floating(a)))
def half(a):return g.u32(((trunc(a)&65535)^32768)-32768)
def data(m,p,n):return bytes(m[p+i]for i in range(n))

def tile_effect(m,c,h):
 if c.mutation&1:
  for off,v in((0x38,19.5),(0x3c,20.25),(0x40,21.75)):put(m,ACTOR+off,g.bits(v))
  for off,v in((8,3.25),(12,7.25),(16,5.75)):put(m,h+off,g.bits(v))

def query_effect(m,c,roles):
 for i,v in enumerate((1.25,-2.5,3.75)):put(m,roles['position']+4*i,g.bits(v))
 for i in range(9):put(m,roles['context']+2*i,(i*37+0xff00)&65535,2)
 put(m,roles['hit'],0xffffffff if c.flags&1 else 7)
 if c.mutation&2:
  put(m,ACTOR+0x128,0x55667788);put(m,ACTOR+0x14c,0x66778899);m[ACTOR+0xc]=0x33

def classify_effect(m,c,roles):
 if c.mutation&4:
  put(m,roles['position']+4,g.bits(22.5));put(m,roles['context']+4,0x11223344)
  put(m,ACTOR+0x168,0x778899aa);put(m,CONSTANTS[0],g.bits(.25))

def rng_effect(m,c,index):
 if c.mutation&16 and index==0:
  put(m,ACTOR+0x128,0x8899aabb);put(m,ACTOR+0x14c,0x99aabbcc);put(m,CONSTANTS[1],g.bits(.5))

def factory_effect(m,c,roles):
 if c.success:
  for i in range(88):m[OUTPUT+0x10+i]=m[roles['burst']+i]
 if c.mutation&8:
  put(m,roles['position'],g.bits(-12.5));put(m,roles['context']+8,0x55667788)
  for off,v in((0x128,0xaabbccdd),(0x14c,0xbbccddee),(0x168,0xccddeeff)):put(m,ACTOR+off,v)
  m[ACTOR+0xc]=0x44;m[ACTOR+1]=7;put(m,CONSTANTS[2],g.bits(.875))

def spray_effect(m,roles):
 for i in range(164):m[SPRAY_OUTPUT+i]=m[roles['spray']+i]

def reference(initial,c,kind='retail',home=None,surface=SURFACE):
 h=STACK+c.phase if home is None else home;m=dict(initial);roles=layout(h,kind);calls=[];obs=[];a=ACTOR
 def field(base,off,v,n=4):put(m,base+off,v,n)
 def rng(index):calls.append((RNG,()));rng_effect(m,c,index);return c.randoms[index]
 vertical=read(m,a+0x48);amplitude=read(m,a+0x140)
 if g.floating(subtract(amplitude,vertical&0x7fffffff))>6.:
  args=(1,*(half(read(m,surface+off))for off in(0x14,0x18,0x1c)));calls.append((TILE,args));tile_effect(m,c,h)
  if not c.tile:
   start=tuple(read(m,h+off)for off in(8,12,16));delta=tuple(subtract(read(m,a+off),v)for off,v in zip((0x38,0x3c,0x40),start))
   args=(*start,*delta,0,roles['context'],roles['position'],roles['position']+4,roles['position']+8,0,roles['hit'],0,0)
   calls.append((QUERY,args));query_effect(m,c,roles)
   if c.query:
    calls.append((CLASSIFY,(read(m,roles['hit']),)));classify_effect(m,c,roles)
    if c.classify:
     d=roles['burst'];extra=roles['extra']
     for off,v,n in((0x54,25,2),(0x56,10,2),(0,4,1),(1,0,1),(2,0x3b02,2)):field(d,off,v,n)
     field(d,4,rng(0)%31+40,2);field(d,8,0);field(d,12,0)
     for off in range(16,20):field(d,off,255,1)
     calls.append((REAL,()));v=g.product(add(g.product(c.floats[0],g.bits(25.)),g.bits(25.)),read(m,CONSTANTS[0]));field(d,0x14,v);field(d,0x18,v)
     for i in range(12):m[d+0x1c+i]=m[roles['position']+i]
     field(d,0x40,0xc5c0001)
     for off,v in((0x44,255),(0x45,255),(0x46,0),(0x47,7)):field(d,off,v,1)
     for off in range(0x28,0x40,4):field(d,off,0)
     calls.append((REAL,()));field(extra,0,g.product(add(g.product(c.floats[1],g.bits(80.)),g.bits(50.)),read(m,CONSTANTS[1])));field(d,0x50,read(m,a+0x128))
     first,second,third=rng(1),rng(2),rng(3)
     args=(d,ASSET,24,0,0,(second&1)+((first&1)<<1),third&255,g.bits(500.),g.bits(500.),0,roles['context'],read(m,a+0x14c),read(m,a+0x168),0,8,m[a+0xc],m[a+1]);calls.append((FACTORY,args));obs.append(('burst',data(m,d,88)));factory_effect(m,c,roles)
     if c.success:
      calls.append((COPY,(OUTPUT+0x128,extra,8)));obs.append(('extra',data(m,extra,8)))
      for i in range(8):m[OUTPUT+0x128+i]=m[extra+i]
    d=roles['spray']
    for i in range(3):field(d,0xc+4*i,delta[i]^0x80000000)
    for i in range(18):m[d+0x18+i]=m[roles['context']+i]
    field(d,0x2c,g.bits(502.))
    for i in range(12):m[d+i]=m[roles['position']+i]
    for off,v in((0x48,6),(0x4a,6),(0x4c,3),(0x4e,3),(0x50,50),(0x52,20),(0x9c,10),(0x9e,25)):field(d,off,v,2)
    for off,v in((0x30,g.bits(3.)),(0x34,g.bits(3.)),(0x38,read(m,CONSTANTS[2])),(0x3c,read(m,CONSTANTS[3])),(0x40,read(m,CONSTANTS[4])),(0x44,read(m,CONSTANTS[5])),(0x58,1),*((off,0)for off in range(0x5c,0x70,4)),(0x74,read(m,a+0x14c)),(0x78,read(m,a+0x168)),(0x7c,0),(0x80,0x220005),(0x84,0x1d0600),(0x88,1),(0x8c,0x3b),(0x90,0x80),(0x94,0x20),(0xa0,read(m,a+0x128))):field(d,off,v)
    for off,v in((0x54,1),(0x55,33),(0x56,72),(0x70,0),(0x71,155),(0x72,100),(0x98,0),(0x99,7)):field(d,off,v,1)
    calls.append((SPRAY,(d,m[a+0xc],m[a+1])));obs.append(('spray',data(m,d,164)));spray_effect(m,roles)
  index=4 if not c.tile and c.query and c.classify else 0
  v=rng(index);calls.append((SOUND,(read(m,SOUNDS+4*(v&1)),32000,0,0,0,*(trunc(read(m,a+off))for off in(0x38,0x3c,0x40)),1000,4000)));result=0
 else:
  put(m,a+0x44,0);put(m,a+0x4c,0)
  if g.floating(vertical)>0:put(m,a+0x48,g.product(vertical,read(m,a+0x14)))
  factor=read(m,a+0x14)
  for dst,src in((0x38,0x14),(0x3c,0x18),(0x40,0x1c)):put(m,a+dst,read(m,surface+src))
  for off in(0x50,0x54,0x58):put(m,a+off,g.product(read(m,a+off),factor))
  calls.append((SOUND,(read(m,ONE_SOUND),64000,0,0,0,*(trunc(read(m,surface+off))for off in(0x14,0x18,0x1c)),1000,4000)));result=1
 return public(m),calls,obs,result

class Oracle(g.Oracle):
 def __init__(self,words,c,kind='retail',initial=None,home=None,surface=SURFACE,entry=ENTRY,connected=None):
  self.cc=c;self.kind=kind;self.i=self.j=0;self.obs=[];self.home=STACK+c.phase if home is None else home;self.roles=layout(self.home,kind);self.surface=surface
  g.Oracle.__init__(self,words,fixture(c,kind,self.home,surface)if initial is None else initial,c,entry=entry,connected=connected)
  self.r[4:8]=[ACTOR,surface,g.bits(2.25),g.bits(6.25)]
 def execute(self,w):
  op,rs,fn=w>>26,w>>21&31,w&63
  if op==17 and rs==16 and fn in(5,7):self.f[w>>6&31]=(self.f[w>>11&31]&0x7fffffff)if fn==5 else self.f[w>>11&31]^0x80000000
  elif op in(42,46):
   at=g.u32(self.r[rs]+((w&65535)^32768)-32768);v=self.r[w>>16&31];k=at&3
   if op==42:self.put(at,v>>(8*k),4-k)
   else:self.put(at&~3,v,k+1)
  else:super().execute(w)
 def record_call(self,t):
  n={TILE:4,QUERY:15,CLASSIFY:1,RNG:0,REAL:0,FACTORY:17,COPY:3,SPRAY:3,SOUND:10}[t];a=tuple(map(g.u32,self.arguments(n)))
  if t==QUERY:a=(self.f[12],self.f[14],*a[2:])
  self.calls.append((t,a))
  if t in(FACTORY,SPRAY,COPY):self.obs.append(('burst'if t==FACTORY else 'spray'if t==SPRAY else'extra',data(self.memory,a[1]if t==COPY else a[0],88 if t==FACTORY else 164 if t==SPRAY else 8)))
 def hook(self,t):
  c=self.cc;a=self.calls[-1][1];value=0x12345678;fvalue=None
  if t==TILE:tile_effect(self.memory,c,self.home);value=c.tile
  elif t==QUERY:query_effect(self.memory,c,self.roles);value=c.query
  elif t==CLASSIFY:classify_effect(self.memory,c,self.roles);value=c.classify
  elif t==RNG:rng_effect(self.memory,c,self.i);value=c.randoms[self.i];self.i+=1
  elif t==REAL:fvalue=c.floats[self.j];self.j+=1
  elif t==FACTORY:factory_effect(self.memory,c,self.roles);value=OUTPUT if c.success else 0
  elif t==COPY:
   for i in range(a[2]):self.memory[a[0]+i]=self.memory[a[1]+i]
   value=a[0]
  elif t==SPRAY:spray_effect(self.memory,self.roles)
  else:assert t==SOUND
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.r[2]=g.u32(value)
  if fvalue is not None:self.f[0]=fvalue

def cases():
 pairs=((-1.,0.),(6.,0.),(6.000001,0.),(7.,1.),(7.000001,1.),(16.,-10.),(16.000002,-10.),(60.,-2.),(float('nan'),1.))
 for index,((amplitude,vertical),tile,query,classify,success,mutation,phase)in enumerate(itertools.product(pairs,(0,1),(0,1),(0,1),(0,1),(0,1,2,4,8,16,30,31),(0,8))):
  flags=index%4
  yield Case(amplitude=g.bits(amplitude),vertical=g.bits(vertical),tile=tile,query=query,classify=classify,success=success,mutation=mutation,phase=phase,flags=flags,coordinate=index%3,randoms=(0xffffffff-flags,flags&1,flags>>1,0xffffff00|flags,flags&1))

def run(state):
 count=0;seen=set();raw_seen=set()
 for c in cases():
  for kind in('retail','raw'):
   initial=fixture(c,kind);want=reference(initial,c,kind);m=Oracle(state[kind+'_words'],c,kind,initial);before,fp=m.r[:],m.f[:];m.run()
   actual=public(m.memory),m.calls,m.obs,m.r[2];assert actual==want,(kind,c,actual[1:],want[1:])
   assert m.r[16:24]==before[16:24]and m.r[28:]==before[28:]and m.f[20:]==fp[20:]
   (seen if kind=='retail' else raw_seen).update(m.visits)
  count+=1
 report=dict(passes=True,cases=count,programs=2,retail_words_visited=len(seen),raw_words_visited=len(raw_seen),unvisited_retail_words=[i for i in range(391)if ENTRY+4*i not in seen],all88_and164_descriptor_bytes=True,all8_extra_bytes=True,collision_metadata_bytes=18,finite_arithmetic_and_defined_s32_conversions=True,provider_mutations=True,hardware_FCSR_or_NaN_payload_identity_claimed=False,source_installed=False,c_match_credit=0)
 (s.OUT/'guest-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
