"""Independent complete descriptor/motion model with deliberate provider mutations."""
from dataclasses import dataclass
import itertools,json,math
from tools.experiments import game_amplitude_terminal_150b89e0_screen as s
from tools.tests import test_game_point_interval_effect_match as g
ENTRY=s.ENTRY;STACK=g.STACK;ACTOR=0x30000;OUTPUT=0x50000;SPRAY_OUTPUT=0x60000
put,read=g.put,g.read;RNG,REAL,FACTORY,SPRAY,SOUND,MATRIX,TRANSFORM,COPY=0x150ADA20,0x150ADA68,0x1513D594,0x15151A38,0x10010F88,0x150A8050,0x150A7960,0x10022EC0
sym=s.symbols();K0,K1,K2=sym['D_8009FDB0'],sym['D_8009FDB4'],sym['D_8009FDB8'];SOUNDS=sym['D_80088734'];ONE_SOUND=sym['D_8008873C'];ASSET=sym['D_800A4AA0']

@dataclass(frozen=True)
class Case:
 actor:int=ACTOR;mode:int=0;amount:int=0;phase:int=0;fcsr:int=0;amplitude:int=0x42000000;success:int=1;mutation:int=0;flags:int=0
 randoms:tuple=(0xffffffff,1,0,255,1);floats:tuple=(0x3f000000,0x3e800000)

def fixture(c):
 h=STACK+c.phase;m={STACK+i:(i*17+165)&255 for i in range(-1536,1024)}
 for base,n in((ACTOR,0x180),(OUTPUT,0x200),(SPRAY_OUTPUT,136)):m.update({base+i:(i*13+91)&255 for i in range(n)})
 for off,v in((4,g.bits(2.25)),(8,g.bits(6.25)),(12,g.bits(4.75)),(16,g.bits(-6.5)),(20,ACTOR+0x114)):put(m,h+off,v)
 for off,v in((0x10,.5),(0x14,.75),(0x20,4.),(0x24,5.),(0x28,6.),(0x38,1.25),(0x3c,-2.5),(0x40,3.75),*((0x44+4*i,float(i+1))for i in range(6))):put(m,ACTOR+off,g.bits(v))
 for off,v in((0x60,0xabcdef01),(0x128,0x12345678),(0x140,c.amplitude),(0x14c,0x23456789),(0x168,0x34567890)):put(m,ACTOR+off,v)
 m[ACTOR+1]=5;m[ACTOR+0xc]=255
 for at,v in((K0,.125),(K1,.25),(K2,.875)):put(m,at,g.bits(v))
 put(m,SOUNDS,0x1234);put(m,SOUNDS+4,0x5678);put(m,ONE_SOUND,0x9abc);return m

def public(m):return{a:v for a,v in m.items()if not STACK-1536<=a<STACK+1024}
def add(a,b):return g.single(g.floating(a)+g.floating(b))
def trunc(a):return g.u32(math.trunc(g.floating(a)))

def rng_effect(m,c,h,index):
 if c.mutation&1 and index==0:
  put(m,ACTOR+0x128,0x778899aa);put(m,ACTOR+0x14c,0x55667788);put(m,K0,g.bits(.25))

def factory_effect(m,c,h,d):
 if c.success:
  for i in range(88):m[OUTPUT+0x10+i]=m[d+i]
 if c.mutation&2:
  for off,v in((4,12.5),(12,-13.5),(16,14.5)):put(m,h+off,g.bits(v))
  for off,v in((0x128,0xabcdef98),(0x14c,0x87654321),(0x168,0x55667788)):put(m,ACTOR+off,v)
  put(m,K2,g.bits(.375));m[ACTOR+0xc]=0x33;m[ACTOR+1]=7

def spray_effect(m,c,h,d):
 for i in range(136):m[SPRAY_OUTPUT+i]=m[d+i]
 if c.mutation&4:put(m,ACTOR+0x38,g.bits(-7.5));put(m,ACTOR+0x40,g.bits(8.5));put(m,h+16,g.bits(-20.5))

def matrix_effect(m,c,q):
 for i in range(16):put(m,q+4*i,g.bits(float(i+1)))
 if c.mutation&8:
  for off,v in((0x38,7.5),(0x3c,8.5),(0x40,9.5)):put(m,ACTOR+off,g.bits(v))

def transform_effect(m,args):
 for at,value in zip(args[4:],(2.5,-3.5,4.5)):put(m,at,g.bits(value))

def reference(initial,c,h=None,point=None):
 h=STACK+c.phase if h is None else h;m=dict(initial);calls=[];obs=[];a=ACTOR;matrix=h-296;d=h-88;extra=h-96;spray=h-232
 if point is not None:
  for off,v in zip((4,8,12,16,20),point):put(m,h+off,v)
 for off,value in((4,read(m,h+4)),(8,read(m,h+8)),(12,read(m,h+12))):put(m,h+off,value)
 amplitude=g.floating(read(m,a+0x140));put(m,a+0x3c,add(read(m,a+0x10),read(m,h+16)))
 def field(base,off,v,n=4):put(m,base+off,v,n)
 def rng(i):calls.append((RNG,()));rng_effect(m,c,h,i);return c.randoms[i]
 if amplitude>15.:
  if amplitude>30.:
   for off,v,n in((0x54,25,2),(0x56,10,2),(0,4,1),(1,0,1),(2,0x3b02,2)):field(d,off,v,n)
   field(d,4,rng(0)%31+40,2);field(d,8,0);field(d,12,0)
   for off in range(16,20):field(d,off,255,1)
   calls.append((REAL,()));value=g.product(add(g.product(c.floats[0],g.bits(25.)),g.bits(25.)),read(m,K0));field(d,0x14,value);field(d,0x18,value)
   for off,home in((0x1c,4),(0x20,16),(0x24,12)):field(d,off,read(m,h+home))
   for off in range(0x28,0x40,4):field(d,off,0)
   field(d,0x40,0xc5c0001)
   for off,v in((0x44,255),(0x45,255),(0x46,0),(0x47,7)):field(d,off,v,1)
   calls.append((REAL,()));put(m,extra,g.product(add(g.product(c.floats[1],g.bits(80.)),g.bits(50.)),read(m,K1)));field(d,0x50,read(m,a+0x128))
   first,second,third=rng(1),rng(2),rng(3)
   args=(d,ASSET,24,0,0,(second&1)+((first&1)<<1),third&255,g.bits(500.),g.bits(500.),0,read(m,h+20),read(m,a+0x14c),read(m,a+0x168),0,8,m[a+0xc],m[a+1]);calls.append((FACTORY,args));obs.append(('burst',g.packet(m,d,88)));factory_effect(m,c,h,d)
   if c.success:
    calls.append((COPY,(OUTPUT+0x128,extra,8)))
    for i in range(8):m[OUTPUT+0x128+i]=m[extra+i]
   for off,home in((0,4),(4,16),(8,12)):field(spray,off,read(m,h+home))
   for off,value in((0xc,g.bits(3.)),(0x10,g.bits(3.)),(0x14,read(m,K2)),(0x18,0),(0x1c,g.bits(10.)),(0x20,g.bits(10.))):field(spray,off,value)
   for off,value in((0x24,6),(0x26,6),(0x28,0),(0x2a,255),(0x2c,-63),(0x2e,29),(0x30,3),(0x32,3),(0x34,50),(0x36,20)):field(spray,off,g.u32(value),2)
   for off,value in((0x38,1),(0x39,33),(0x3a,72),(0x54,0),(0x55,155),(0x56,100),(0x7c,0),(0x7d,7)):field(spray,off,value,1)
   for off,value in((0x3c,1),*((off,0)for off in range(0x40,0x54,4)),(0x58,read(m,a+0x14c)),(0x5c,read(m,a+0x168)),(0x60,0),(0x64,0x220005),(0x68,0x1d0600),(0x6c,1),(0x70,0x3b),(0x74,0x80),(0x78,0x20),(0x84,read(m,a+0x128))):field(spray,off,value)
   field(spray,0x80,10,2);field(spray,0x82,25,2);calls.append((SPRAY,(spray,m[a+0xc],m[a+1])));obs.append(('spray',g.packet(m,spray,136)));spray_effect(m,c,h,spray)
   value=rng(4);calls.append((SOUND,(read(m,SOUNDS+4*(value&1)),32000,0,0,0,trunc(read(m,a+0x38)),trunc(add(read(m,h+16),g.bits(25.))),trunc(read(m,a+0x40)),1000,4000)));result=0
  else:
   factor=read(m,a+0x14)
   for off in range(0x44,0x5c,4):put(m,a+off,g.product(read(m,a+off)^(0x80000000 if off==0x48 else 0),factor))
   calls.append((SOUND,(read(m,ONE_SOUND),32000,0,0,0,trunc(read(m,a+0x38)),trunc(read(m,a+0x3c)),trunc(read(m,a+0x40)),1000,4000)));result=1
 else:
  m[a+0x72]=m[a+0x78]=1;put(m,a+0x60,read(m,a+0x60)&0xffffff00);args=(matrix,read(m,a+0x20),read(m,a+0x24),read(m,a+0x28));calls.append((MATRIX,args));matrix_effect(m,c,matrix)
  args=(matrix,0,0,g.bits(200.),a+0x20,a+0x24,a+0x28);calls.append((TRANSFORM,args));obs.append(('matrix',g.packet(m,matrix,64)));transform_effect(m,args)
  for pos,vel in((0x20,0x38),(0x24,0x3c),(0x28,0x40)):put(m,a+pos,add(read(m,a+pos),read(m,a+vel)))
  result=1
 return public(m),calls,obs,result

class Oracle(g.Oracle):
 def __init__(self,words,c):
  self.cc=c;self.i=self.j=0;self.obs=[];g.Oracle.__init__(self,words,fixture(c),c,entry=ENTRY);self.home=STACK+c.phase;self.r[4:8]=[ACTOR,g.bits(2.25),g.bits(6.25),g.bits(4.75)]
 def execute(self,w):
  if w>>26==17 and w>>21&31==16 and w&63==7:self.f[w>>6&31]=self.f[w>>11&31]^0x80000000
  else:super().execute(w)
 def record_call(self,t):
  n={RNG:0,REAL:0,FACTORY:17,SPRAY:3,SOUND:10,MATRIX:4,TRANSFORM:7,COPY:3}[t];a=tuple(map(g.u32,self.arguments(n)));self.calls.append((t,a))
  if t in(FACTORY,SPRAY):self.obs.append(('burst'if t==FACTORY else'spray',g.packet(self.memory,a[0],88 if t==FACTORY else 136)))
  if t==TRANSFORM:self.obs.append(('matrix',g.packet(self.memory,a[0],64)))
 def hook(self,t):
  c=self.cc;a=self.calls[-1][1];value=0x12345678;fvalue=None
  if t==RNG:rng_effect(self.memory,c,self.home,self.i);value=c.randoms[self.i];self.i+=1
  elif t==REAL:fvalue=c.floats[self.j];self.j+=1
  elif t==FACTORY:factory_effect(self.memory,c,self.home,a[0]);value=OUTPUT if c.success else 0
  elif t==SPRAY:spray_effect(self.memory,c,self.home,a[0])
  elif t==MATRIX:matrix_effect(self.memory,c,a[0])
  elif t==TRANSFORM:transform_effect(self.memory,a)
  elif t==COPY:
   for i in range(a[2]):self.memory[a[0]+i]=self.memory[a[1]+i]
   value=a[0]
  elif t!=SOUND:raise AssertionError(hex(t))
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.r[2]=g.u32(value)
  if fvalue is not None:self.f[0]=fvalue

def run(state):
 values=(g.bits(-1.),g.bits(0.),g.bits(15.),g.bits(15.000001),g.bits(30.),g.bits(30.000002),g.bits(60.),0x7fc00001,0x7f800000)
 count=0;seen=set()
 for amplitude,success,mutation,phase,flags in itertools.product(values,(0,1),range(16),(0,8),range(4)):
  c=Case(amplitude=amplitude,success=success,mutation=mutation,phase=phase,flags=flags,randoms=(0xffffffff-flags,flags&1,flags>>1,0xffffff00|flags,flags&1));want=reference(fixture(c),c)
  for words in(state['raw_words'],state['retail_words']):
   m=Oracle(words,c);before,fp=m.r[:],m.f[:];m.run();actual=public(m.memory),m.calls,m.obs,g.u32(m.r[2]);assert actual==want,(c,actual[1:],want[1:])
   assert m.r[16:24]==before[16:24]and m.r[28:]==before[28:]and m.f[20:]==fp[20:]
   if words is state['retail_words']:seen.update(m.visits)
  count+=1
 report=dict(passes=True,cases=count,programs=2,retail_words_visited=len(seen),unvisited_words=[i for i in range(345)if ENTRY+4*i not in seen],all88_and136_descriptor_bytes=True,all8_extra_bytes=True,all64_matrix_bytes=True,provider_mutations=True,source_installed=False,c_match_credit=0)
 (s.OUT/'guest-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
